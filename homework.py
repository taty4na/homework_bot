"""Бот отправляет в чат результат проверки домашней  работы."""
import logging
import os
import time
from http import HTTPStatus
from json.decoder import JSONDecodeError

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except TelegramError:
        logger.error('Сообщение не отправлено')
        raise TelegramError('Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if homework_statuses.status_code != HTTPStatus.OK:
            logger.error('Произошла ошибка HTTP')
            raise ConnectionError('Произошла ошибка HTTP')
    except ConnectionError:
        logger.error('Произошла ошибка подключения')
        raise ConnectionError('Произошла ошибка подключения')
    except requests.exceptions.URLRequired as erru:
        logger.error('Недействительный URL-адрес')
        raise erru('Недействительный URL-адрес')
    except requests.exceptions.RequestException as err:
        logger.error('Ошибка - нет ответа')
        raise err('Ошибка - нет ответа')
    try:
        return homework_statuses.json()
    except JSONDecodeError:
        logger.error('У ответа нет формата JSON')
        raise JSONDecodeError('У ответа нет формата JSON')


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        logger.error('Тип ответа не соответствует ожиданиям')
        raise TypeError('Тип ответа не соответствует ожиданиям')
    if not isinstance(homeworks, list):
        logger.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    else:
        return homeworks


def parse_status(homework):
    """Возвращает строку, содержащую вердикт о проверке."""
    if 'homework_name' not in homework:
        logger.error('Нет ключа homework_name')
        raise KeyError('Нет ключа homework_name')
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        logger.error('Нет ключа status')
        raise KeyError('Нет ключа status')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logger.error('Неизвестный статус')
        raise KeyError('Неизвестный статус')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        logger.error('Ошибка TOKEN')
        return False


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, stack_info=True)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
