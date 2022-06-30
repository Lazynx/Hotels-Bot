from loader import bot
from config_data import config as c
from utils import work_with_api as api
from states.user_information import UserInfoState

import json
import re

from telegram_bot_calendar import WYearTelegramCalendar
import datetime

from loguru import logger

from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from requests import Response


class MyStyleCalendar(WYearTelegramCalendar):
    """ Класс календаря для кастомизации. """
    prev_button = "⬅️"
    next_button = "➡️"
    empty_month_button = ""
    empty_year_button = ""


def form_media_group(photos: list, text: str) -> list:
    """ Функция для формирования медиагруппы, если возникла ошибка, то производим проверку ссылок в группе """
    media = []
    num = 0
    for photo in photos:
        if api.check_foto(photo[1]):
            media.append(InputMediaPhoto(media=photo[1], caption=text if num == 0 else ''))
            num += 1
        else:
            continue
    return media


def city_founding(response: Response) -> list:
    """ Функция для формирования списка городов. """
    pattern = r'(?<="CITY_GROUP",).+?[\]]'
    find = re.search(pattern, response)
    suggestions = []
    if find:
        suggestions = json.loads(f"{{{find[0]}}}")
    cities = list()
    for dest_id in suggestions['entities']:  # Обрабатываем результат
        clear_destination = re.sub(r"<span class='highlighted'>(.*)</span>", r'\1', dest_id['caption'])
        if re.search(r"</span>(.*)<span class='highlighted'>", clear_destination):
            full_clear_destination = re.sub(r"</span>(.*)<span class='highlighted'>", '-', clear_destination)
            cities.append({'city_name': full_clear_destination, 'destination_id': dest_id['destinationId']})
        else:
            cities.append({'city_name': clear_destination, 'destination_id': dest_id['destinationId']})
    return cities


def city_markup(message: Message) -> InlineKeyboardMarkup:
    """ Клавиатура для выбора конкретного города. """
    cities = city_founding(message)
    destinations = InlineKeyboardMarkup()
    for i_city in cities:
        destinations.add(InlineKeyboardButton(text=i_city['city_name'],
                                              callback_data=f'{i_city["destination_id"]}'))

    return destinations


@bot.callback_query_handler(func=lambda call: call.data.isdigit())
def get_city_id(call: CallbackQuery) -> None:
    """ Функция для получения ID города. """
    if call.message:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info('ID города: {}'.format(call.data))
        bot.set_state(call.from_user.id, UserInfoState.city_id, call.message.chat.id)
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data['city_id'] = call.data
        today = datetime.date.today()
        calendar, step = get_calendar(calendar_id=1,
                                      current_date=today,
                                      min_date=today,  # Старые даты отбрасываем они нас навряд ли интересуют
                                      max_date=today + datetime.timedelta(days=365),
                                      # Чтобы максимальное значение дат было +1 год
                                      locale="ru")

        bot.set_state(call.from_user.id, UserInfoState.check_in, call.message.chat.id)
        bot.send_message(call.from_user.id, 'Отлично, выберите дату заезда:')
        bot.send_message(call.from_user.id, f"Выберите {c.LSTEP[step]}:", reply_markup=calendar)


def get_calendar(is_process=False, callback_data=None, **kwargs) -> WYearTelegramCalendar:
    """ Функция, которая создает календарь с датами. """
    if is_process:
        result, key, step = MyStyleCalendar(calendar_id=kwargs['calendar_id'],
                                            current_date=kwargs.get('current_date'),
                                            min_date=kwargs['min_date'],
                                            max_date=kwargs['max_date'],
                                            locale=kwargs['locale']).process(callback_data.data)
        return result, key, step
    else:
        calendar, step = MyStyleCalendar(calendar_id=kwargs['calendar_id'],
                                         current_date=kwargs.get('current_date'),
                                         min_date=kwargs['min_date'],
                                         max_date=kwargs['max_date'],
                                         locale=kwargs['locale']).build()
        return calendar, step


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=1))
def get_check_in(call: CallbackQuery) -> None:
    """ Функция для получения даты въезда. """
    today = datetime.date.today()
    result, key, step = get_calendar(calendar_id=1,
                                     current_date=today,
                                     min_date=today,
                                     max_date=today + datetime.timedelta(days=365),
                                     locale="ru",
                                     is_process=True,
                                     callback_data=call)
    if not result and key:
        bot.edit_message_text(f"Выберите {c.LSTEP[step]}:",
                              call.from_user.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data['check_in'] = result
            logger.info('Дата заезда: {}'.format(result))

            bot.delete_message(call.message.chat.id, call.message.message_id - 1)
            bot.edit_message_text(f"Дата заезда {result}",
                                  call.message.chat.id,
                                  call.message.message_id)

            bot.send_message(call.from_user.id, "Выберите дату выезда:")
            calendar, step = get_calendar(calendar_id=2,
                                          min_date=result + datetime.timedelta(days=1),
                                          max_date=result + datetime.timedelta(days=365),
                                          locale="ru",
                                          )

            bot.send_message(call.from_user.id,
                             f"Выберите {c.LSTEP[step]}:",
                             reply_markup=calendar)
            bot.set_state(call.from_user.id, UserInfoState.check_out, call.message.chat.id)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=2))
def get_check_out(call: CallbackQuery) -> None:
    """ Функция для получения даты выезда. """
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        result, key, step = get_calendar(calendar_id=2,
                                         current_date=data['check_in'],
                                         min_date=data['check_in'] + datetime.timedelta(days=1),
                                         max_date=data['check_in'] + datetime.timedelta(days=365),
                                         locale="ru",
                                         is_process=True,
                                         callback_data=call)
        if not result and key:
            bot.edit_message_text(f"Выберите {c.LSTEP[step]}:",
                                  call.from_user.id,
                                  call.message.message_id,
                                  reply_markup=key)

        elif result:
            data['check_out'] = result
            logger.info('Дата выезда: {}'.format(data['check_out']))
            bot.delete_message(call.message.chat.id, call.message.message_id - 1)

            bot.edit_message_text(f"Дата выезда {result}",
                                  call.message.chat.id,
                                  call.message.message_id)
            bot.send_message(call.from_user.id, text='Введите кол-во отелей, которое нужно вывести\n'
                                                     '(максимум 10):')


@bot.message_handler(state=UserInfoState.check_out)
def get_hotels_amt(message: Message) -> None:
    """ Функция для получения количества отелей. """
    if message.text.isdigit() and 0 < int(message.text) <= 10:
        bot.send_message(message.from_user.id, text='Необходима ли загрузка фото?\n'
                                                    'Да/Нет')
        bot.set_state(message.from_user.id, UserInfoState.hotels_amt, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['hotels_amt'] = int(message.text)
            logger.info('Кол-во отелей: {}'.format(int(message.text)))
    else:
        bot.send_message(message.from_user.id, text='Я тебя не понял! Введите число от 1 до 10:')


@bot.message_handler(state=UserInfoState.hotels_amt)
def need_photo(message: Message) -> None:
    """ Функция, которая служит для обработки режима просмотра фотографий. """
    if message.text.lower() == 'да':
        bot.send_message(message.from_user.id, text='Хорошо, какое кол-во фото отеля нужно вывести\n'
                                                    '(не больше 5)?')
        bot.set_state(message.from_user.id, UserInfoState.picture_mode, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['picture_mode'] = True
            logger.info('Выбран режим с просмотром фотографий')
    elif message.text.lower() == 'нет':
        bot.send_message(message.from_user.id, text='Хорошо, начинаю загрузку отелей...')
        bot.set_state(message.from_user.id, UserInfoState.photos_amt, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['photos_amt'] = 0
            logger.info('Выбран режим без просмотра фотографий')
        print_hotels(message)
    else:
        bot.send_message(message.from_user.id, text='Я тебя не понял! Введи Да или Нет:')


@bot.message_handler(state=UserInfoState.picture_mode)
def get_photos_amt(message: Message) -> None:
    """ Функция для получения количества фотографий отеля. """
    if message.text.isdigit() and 0 < int(message.text) <= 5:
        bot.set_state(message.from_user.id, UserInfoState.photos_amt, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            bot.send_message(message.from_user.id, text='Отлично, начинаю загрузку отелей...')
            data['photos_amt'] = int(message.text)
            logger.info('Кол-во фото, которое нужно загрузить: {}'.format(int(message.text)))
        print_hotels(message)
    else:
        bot.send_message(message.from_user.id, text='Я тебя не понял! Введите число от 1 до 5:')


def print_hotels(message: Message) -> None:
    """ Функция для вывода информации и фото отеля. """
    parse_list = api.get_hotels_list(message)
    hotels = api.process_hotels_list(parse_list, message)
    if len(hotels) > 0:
        bot.delete_message(message.chat.id, message.message_id + 1)
        bot.send_message(message.from_user.id, text='Результаты поиска:')
        for hotel in hotels:
            text = f"🏨 Название отеля: {hotel[1]}" \
                   f"\n🌐 Сайт: https://www.hotels.com/ho{hotel[0]}" \
                   f"\n🌎 Адрес: {hotel[2]}" \
                   f"\n📌 Открыть в Google maps: http://maps.google.com/maps?z=12&t=m&q=loc:{hotel[7]}" \
                   f"\n↔ Расстояние от центра: {hotel[3]}" \
                   f"\n1️⃣ Цена за сутки: {hotel[4]} RUB" \
                   f"\n💳 Цена за период ({hotel[8].days} дн.): {hotel[5]} RUB" \
                   f"\n⭐ Рейтинг: {hotel[6]}"
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                if data['photos_amt'] > 0:
                    photos = api.request_photo(id_hotel=hotel[0], message=message)
                    media = form_media_group(photos=photos, text=text)
                    bot.send_media_group(chat_id=message.chat.id, media=media)
                else:
                    bot.send_message(chat_id=message.chat.id, text=text, disable_web_page_preview=True)
        logger.info('Вся информация об отелях выведена успешно!')
    else:
        bot.send_message(message.from_user.id, text='Произошла ошибка, повторите попытку.')


@bot.message_handler(commands=['lowprice'])
def start(message: Message) -> None:
    mess = bot.send_message(message.chat.id, 'Какой город вас интересует?')
    bot.register_next_step_handler(message=mess, callback=get_city_name)


def get_city_name(message: Message) -> None:
    """ Функция для получения названия города пользователя. """
    user_city = message.text
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": user_city, "locale": "ru_RU"}
    user_response = api.get_request(url=url, headers=c.headers, params=querystring).text
    if json.loads(user_response)["moresuggestions"] > 0:
        bot.set_state(message.from_user.id, UserInfoState.city_name, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['city_name'] = user_city
            logger.info('Пользователь с айди: {}'.format(message.from_user.id))
            logger.info('Выбран город: {}'.format(user_city))
        bot.send_message(message.from_user.id, 'Уточните, пожалуйста:', reply_markup=city_markup(user_response))
    else:
        bot.send_message(message.from_user.id, text='Данный город не найден!')
        start(message)
