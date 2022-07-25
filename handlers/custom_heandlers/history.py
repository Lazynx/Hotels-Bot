from loader import bot
from database import work_with_db as db
from loguru import logger

from telebot.types import Message


@bot.message_handler(commands=['history'])
def print_history(message: Message) -> None:
    """
    Функция "print_history" формирует и выводит историю пользователя.
    :param message: Сообщение пользователя
    """
    req_list = db.get_info_from_db(message.from_user.id)
    logger.info('История получена из БД.')
    for i_req in req_list:
        text = f'{i_req[0]}  <b>{i_req[1]}</b>\n' \
               f'{i_req[2]}\n'
        for i_hotel in i_req[3]:
            text += f'{i_hotel[0]}\n' \
                    f'{i_hotel[1]}\n'
        bot.send_message(message.from_user.id, text=text, disable_web_page_preview=True, parse_mode='html')
