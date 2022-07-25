from telebot.types import Message

from loader import bot


@bot.message_handler(state=None)
def bot_echo(message: Message):
    """
    Функция "bot_echo" обрабатывает случайный ввод пользователя
    :param message: Сообщение пользователя
    """
    bot.reply_to(message, 'Я тебя не понял, для просмотра моих команд напишите /help')
