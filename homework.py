import sys
import os
import requests
import time
import logging
from http import HTTPStatus
from typing import Optional, Dict, Any, List

from telebot import TeleBot
from dotenv import load_dotenv

from exceptions.api_error import PracticumApiError


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
        homework_statuses = requests.get(
            url=ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        if homework_statuses.status_code == HTTPStatus.NOT_FOUND:
            raise PracticumApiError
        return homework_statuses.json()
    except PracticumApiError:
        logger.error(
            f'Сбой в работе программы: Эндпоинт: {ENDPOINT} недоступен. '
            f'Код ответа API: {homework_statuses.status_code}.'
        )


def check_response(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Проверяет данные из словаря response."""
    try:
        if (
            'homeworks' not in response
            or 'current_date' not in response
        ):
            logger.error(
                'Отсутствие обязательного ключа в словаре.'
            )
        elif not response.get('homeworks'):
            logger.debug(
                'Список домашек пуст.'
            )
    except KeyError:
        logger.error(
            'В словаре из API-домашки отсутствуют ключи ключ `homeworks` '
            'или `current_date`.'
        )
    except TypeError:
        logger.error(
            'В словаре из API-домашки под ключом `homeworks `'
            'должен быть список словарей.'
        )
    return response.get('homeworks')


def parse_status(homework: Dict[str, Any]) -> Optional[str]:
    """
    Разбирает данные из словаря, подготавливает
    данные для отправки изменений.
    """
    if not homework:
        logger.error('Пустой ответ от API Яндекс Домашка.')
        return
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status not in HOMEWORK_VERDICTS:
        logger.error('Неверный формат данных для домашней работы.')
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
