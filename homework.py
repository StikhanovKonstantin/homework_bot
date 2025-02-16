import sys
import os
import requests
import time
import logging
from http import HTTPStatus
from typing import Optional, Any

from telebot import TeleBot
from dotenv import load_dotenv

from exceptions.api_request_error import ApiHomeworkError


load_dotenv()

logger = logging.getLogger(__name__)


PRACTICUM_TOKEN: Optional[str] = os.getenv('PRACT_TOKEN')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('USER_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Возвращает True, если все переменные окружения на месте."""
    tokens: dict[str, Optional[str]] = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens: list[str] = [
        name for name, token in tokens.items() if not token
    ]
    if missing_tokens:
        logger.critical(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}.'
        )
        raise EnvironmentError(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}.'
        )
    return True


def send_message(bot: TeleBot, message: str) -> bool:
    """Отправляет сообщение пользователю в чат Телеграмм."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.debug(f'Сообщение отправлено успешно: {message}.')


def get_api_answer(timestamp: int) -> dict[str, Any]:
    """Получает ответ с API-сервиса Яндекс Домашка."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException as e:
        raise ConnectionError(
            f'Ошибка запроса к API. Получена ошибка: {e}.'
        ) from e

    if response.status_code != HTTPStatus.OK:
        raise ApiHomeworkError(
            f'Ошибка HTTP: статус-код - {response.status_code}. '
            f'Ожидался статус: {HTTPStatus.OK}'
        )
    try:
        response_data = response.json()
    except ValueError as e:
        raise ValueError('Ошибка декодирования JSON из ответа API') from e
    return response_data


def check_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Проверяет данные из словаря API, проверяет на наличие ключей и формата.

    Ожидается, что response - словарь с ключами:
    'homeworks' - список домашних заданий(1 задание - словарь);
    'current_date' - числовое значение(формат UNIX-время).

    Возвращает список домашних заданий.
    """
    keys: set = {'homeworks', 'current_date'}
    if not isinstance(response, dict):
        raise TypeError('Ожидался словарь с данными API.')
    for key in keys:
        if key not in response:
            raise KeyError(
                f'Обязательный ключ `{key}` отсутсвует в словаре API.'
            )
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Значение под ключом `homeworks` должно быть списком!')
    if not homeworks:
        raise ValueError('Список домашек пуст.')

    return homeworks


def parse_status(homework: dict[str, Any]) -> Optional[str]:
    """
    Разбирает данные из словаря с домашней работой.

    Ожидается, что в словаре `homework` должны быть ключи:
    `homework_name` - название домашки;
    `homework_status` - статус домашки(успешно, отклонена, взята на проверку);

    Подготавливает данные для отправки сообщения в Телеграмм.
    """
    if not homework:
        raise ValueError('Пустой ответ от API Яндекс Домашка.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Неверный формат данных для домашней работы.')
    verdict = HOMEWORK_VERDICTS.get(homework_status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # Проверяем наличие всех переменных окружения.
    if not check_tokens():
        exit
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
                try:
                    send_message(bot, f'Сбой в работе программы: {e}')
                except Exception as e:
                    logger.error(
                        f'Не удалось отправить сообщение об ошибке: {e}.'
                    )
                last_error_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    # Настраиваем логирование.
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    main()
