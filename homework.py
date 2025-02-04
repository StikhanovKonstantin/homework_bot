import sys
import os
import requests
import time
import logging
from http import HTTPStatus
from typing import Optional, Dict, Any, List

from telebot import TeleBot
from dotenv import load_dotenv


load_dotenv()


# Настраиваем логирование.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN: Optional[str] = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('USER_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: Dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: Dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Возвращает True, если все переменные окружения на месте."""
    tokens: Dict[str, Optional[str]] = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for name, token in tokens.items():
        if not token:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {name}. '
                'Программа остановлена принудительно.'
            )
            return False
    return True


def send_message(bot: TeleBot, message: str) -> None:
    """Отправляет сообщение пользователю в чат Телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено успешно: {message}.')
    except Exception as e:
        logger.error(f'Не удалось отправить сообщение: {e}.')


def get_api_answer(timestamp: int) -> Dict[str, Any]:
    """Получает ответ с API-сервиса Яндекс Домашка."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException as e:
        message = f'Ошибка запроса к API. Получена ошибка: {e}.'
        logger.error(message)
        return {}
    if response.status_code != HTTPStatus.OK:
        raise requests.HTTPError(
            f'Ошибка HTTP: статус-код - {response.status_code}. '
            f'Ожидался статус: {HTTPStatus.OK}'
        )
    try:
        response_data = response.json()
    except ValueError as e:
        message = 'Ошибка декодирования JSON из ответа API'
        logger.error(message)
        raise ValueError(message) from e
    return response_data


def check_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Проверяет данные из словаря API, проверяет на наличие ключей и формата.

    Ожидается, что response - словарь с ключами:
    'homeworks' - список домашних заданий(1 задание - словарь);
    'current_date' - числовое значение(формат UNIX-время).

    Возвращает список домашних заданий.
    """
    # Множество хранит обязательные ключи из словаря API.
    keys: set = {'homeworks', 'current_date'}
    # Проверяем на нужную структуру данных.
    if not isinstance(response, dict):
        logger.error('Ожидался словарь с данными API.')
        raise TypeError
    # Проверяем наличие всех ключей.
    for key in keys:
        if key not in response:
            logger.error(
                f'Обязательный ключ `{key}` отсутсвует в словаре API.'
            )
            raise KeyError
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error('Значение под ключом `homeworks` должно быть списком!')
        raise TypeError
    if not homeworks:
        logger.error('Список домашек пуст.')
        raise ValueError

    return homeworks


def parse_status(homework: Dict[str, Any]) -> Optional[str]:
    """
    Разбирает данные из словаря с домашней работой.

    Ожидается, что в словаре `homework` должны быть ключи:
    `homework_name` - название домашки;
    `homework_status` - статус домашки(успешно, отклонена, взята на проверку);

    Подготавливает данные для отправки сообщения в Телеграмм.
    """
    if not homework:
        logger.error('Пустой ответ от API Яндекс Домашка.')
        return
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        logger.error('Неверный формат данных для домашней работы.')
        raise KeyError
    verdict = HOMEWORK_VERDICTS.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # Проверяем наличие всех переменных окружения.
    token_availability = check_tokens()
    if not token_availability:
        return
    # Переменная будет хранить в себе последнее сообщение об ошибке.
    last_error_message: Optional[str] = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message:
                    send_message(bot, message)
            timestamp = response.get('current_date', timestamp)
            last_error_message = None

        except Exception as e:
            error_message = f'Сбой в работе программы: {e}'
            logger.error(error_message)
            # Если текущая ошибка отличается от предыдущей,
            # то присылаем сообщение в чат Телеграмм.
            if error_message != last_error_message:
                send_message(bot, f'Сбой в работе программы: {e}')
                last_error_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
