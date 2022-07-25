import os
from dotenv import load_dotenv, find_dotenv

if not find_dotenv():
    exit('Переменные окружения не загружены т.к отсутствует файл .env')
else:
    load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
RAPID_API_KEY = os.getenv('RAPID_API_KEY')
LSTEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}
headers = {
    "X-RapidAPI-Key": "dc416aba0amsh25bebf112d7c727p149146jsn710d73390e33",
    "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
}
DEFAULT_COMMANDS = (
    ('start', "Запустить бота"),
    ('help', "Помощь по командам бота"),
    ('lowprice', "Вывод самых дешёвых отелей в городе"),
    ('highprice', "Вывод самых дорогих отелей в городе"),
    ('bestdeal', "Вывод отелей, наиболее подходящих\nпо цене и расположению от центра"),
    ('history', "Вывод истории поиска отелей.")
)
