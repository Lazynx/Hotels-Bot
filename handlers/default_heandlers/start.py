from telebot.types import Message

from loader import bot


@bot.message_handler(commands=['start'])
def bot_start(message: Message):
    """
    Функция "bot_start" обрабатывает команду '/start'
    :param message: Сообщение пользователя
    """
    bot.reply_to(message, f"Привет, {message.from_user.full_name}! Чтобы просмотреть команды бота нажмите /help")
