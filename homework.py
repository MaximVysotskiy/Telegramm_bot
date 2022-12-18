import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from json.decoder import JSONDecodeError

from exceptions import RequestException, APIstatusCodeNot200, ParseStatusError
from endpoints import ENDPOINT

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверка доступности необходимых токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot: telegram.Bot, message: str) -> bool:
    """Функция send_message отправляет сообщение в Telegram чат."""
    try:
        logging.info(f'Бот начал отправку сообщения в Telegram {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение {message}')
    except telegram.error.TelegramError as error:
        logging.error(f'Telegram error: {error}')


def get_api_answer(timestamp: int) -> str:
    """Делаем запрос на сервер ЯП."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            err_msg = 'Код запроса не 200 и равен: {}.'.format(
                response.status_code)
            raise APIstatusCodeNot200(err_msg)
        return response.json()
    except JSONDecodeError as error:
        raise RequestException(f'Ошибка преобразования json {error}')
    except requests.RequestException as error:
        raise RequestException(f'Что то пошло не так {error}')
     

def check_response(response: dict) -> list:
    """Проверяет ответ API."""
    logging.info(f'Начало проверки ответа сервера')
    if not isinstance(response, dict):
        raise TypeError('Ответ от API не является словарём')
    if 'homeworks' not in response:
        raise KeyError(f'Ключ "homeworks" не найден в {response}')
    if 'current_date' not in response:
        raise KeyError(f'Ключ "current_date" не найден в {response}')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В ключе "homeworks" нет списка')
    homeworks = response.get('homeworks')
    if not homeworks:
        raise KeyError('В ключе "homeworks" нет значений')
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлеает информацию о статусе домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в отвте API')
    homework_name = homework['homework_name']
    homework_status = homework.get('status')
    if 'status' not in homework:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)
        raise ParseStatusError(message)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Недокументированный статус домашней работы'
        logging.error(message)
        raise KeyError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.\n'
            'Программа принудительно остановлена.'
        )
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Ответ API пуст: нет домашних работ.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(stream=sys.stdout)])
    main()
