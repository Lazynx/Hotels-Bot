from loader import bot
from config_data import config as c
from utils import work_with_api as api
from states.user_information import UserInfoState
from database import work_with_db as db

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
    """
    Функция "form_media_group" нужна для:
    1. Формирования медиа группы.
    """
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
    """
    Функция "city_founding" нужна для:
    1. Формирования списка городов.
    """
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
    """
    Функция "city_markup" нужна для:
    1. Формирования клавиатуры с выбором конкретного города.
    """
    cities = city_founding(message)
    destinations = InlineKeyboardMarkup()
    for i_city in cities:
        destinations.add(InlineKeyboardButton(text=i_city['city_name'],
                                              callback_data=f'{i_city["destination_id"]}'))

    return destinations


@bot.callback_query_handler(func=lambda call: call.data.isdigit())
def get_city_id(call: CallbackQuery) -> None:
    """
    Функция "get_city_id" нужна для:
    1. Получения ID города и записи состояния об этом.
    2.Если выбрана команда - '/bestdeal', то опрос пользователя о диапазоне цен.
      Если две другие, то опрос пользователя о дате заезда.
    """
    if call.message:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        logger.info('ID города: {}'.format(call.data))
        bot.set_state(call.from_user.id, UserInfoState.city_id, call.message.chat.id)
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data['city_id'] = call.data
            if data['commands'] == 'bestdeal':
                bot.send_message(call.from_user.id, 'Введите диапазон цен\n'
                                                    '(через пробел или -):')
            else:
                today = datetime.date.today()
                calendar, step = get_calendar(calendar_id=1,
                                              current_date=today,
                                              min_date=today,
                                              max_date=today + datetime.timedelta(days=365),
                                              locale="ru")

                bot.set_state(call.from_user.id, UserInfoState.check_in, call.message.chat.id)
                bot.send_message(call.from_user.id, 'Отлично, выберите дату заезда:')
                bot.send_message(call.from_user.id, f"Выберите {c.LSTEP[step]}:", reply_markup=calendar)


@bot.message_handler(state=UserInfoState.city_id)
def get_prices(message: Message) -> None:
    """
    Функция "get_prices" нужна для:
    1. Получения диапазона цен за отель и записи состояния об этом.
    2. Опроса пользователя об максимальной удаленности от центра.
    """
    try:
        prices = re.split(r'\D', message.text)
        min_price, max_price = int(prices[0]), int(prices[1])
        if 1 < min_price < max_price:
            bot.set_state(message.from_user.id, UserInfoState.min_price, message.chat.id)
            bot.set_state(message.from_user.id, UserInfoState.max_price, message.chat.id)
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['min_price'] = min_price
                data['max_price'] = max_price
                logger.info('Мин. цена - {}   Макс. цена - {}'.format(data['min_price'], data['max_price']))
            bot.send_message(message.from_user.id, 'Введите максимальную удаленность от центра (км.):')
        else:
            raise IndexError
    except (IndexError, TypeError):
        bot.send_message(message.from_user.id, text='Ошибка, повторите попытку ввода диапазона цен.')


@bot.message_handler(state=UserInfoState.max_price)
def get_distances(message: Message) -> None:
    """
    Функция "get_distances" нужна для:
    1. Получения максимальной удаленности отеля от центра и записи состояния об этом.
    """
    if message.text.isdigit() and float(message.text) > 0:
        bot.set_state(message.from_user.id, UserInfoState.distance, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['distance'] = float(message.text)
            logger.info('Расстояние до центра: {}'.format(data['distance']))
        today = datetime.date.today()
        calendar, step = get_calendar(calendar_id=1,
                                      current_date=today,
                                      min_date=today,
                                      max_date=today + datetime.timedelta(days=365),
                                      locale="ru")

        bot.set_state(message.from_user.id, UserInfoState.check_in, message.chat.id)
        bot.send_message(message.from_user.id, 'Отлично, выберите дату заезда:')
        bot.send_message(message.from_user.id, f"Выберите {c.LSTEP[step]}:", reply_markup=calendar)
    else:
        bot.send_message(message.from_user.id, text='Ошибка, повторите попытку ввода расстояния.')


def get_calendar(is_process=False, callback_data=None, **kwargs) -> WYearTelegramCalendar:
    """
    Функция "get_calendar" нужна для:
    1. Создания календаря с текущими датами.
    """
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
    """
    Функция "get_check_in" нужна для:
    1. Отправке пользователю клавиатуры с датами заезда
    2. Записи в состояния дату заезда.
    3. Опроса пользователя о дате выезда.
    """
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
            bot.edit_message_text(f"🔜 Дата заезда {result}",
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
    """
    Функция "get_check_out" нужна для:
    1. Отправке пользователю клавиатуры с датами выезда.
    2. Записи в состояния дату выезда.
    3. Опроса пользователя о кол-во отелей, которое нужно вывести.
    """
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

            bot.edit_message_text(f"🔙 Дата выезда {result}",
                                  call.message.chat.id,
                                  call.message.message_id)
            bot.send_message(call.from_user.id, text='Введите кол-во отелей, которое нужно вывести\n'
                                                     '(максимум 10):')


@bot.message_handler(state=UserInfoState.check_out)
def get_hotels_amt(message: Message) -> None:
    """
    Функция "get_hotels_amt" нужна для:
    1. Записи в состояния кол-во отелей.
    2. Опроса пользователя о необходимости загрузки фотографий отеля.
    """
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
    """
    Функция "need_photo" нужна для:
    1. Обработки режима просмотра фотографий:
        * Если пользователь ответил - 'да', то функция записывает состояние и запрашивает кол-во этих фотографий.
        * Если пользователь ответил - 'нет', то функция записывает состояние и начинает вывод отелей.
    """
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
    """
    Функция "get_photos_amt" нужна для:
    1. Получения кол-ва фотографий отеля от пользователя и записи их в состояния.
    """
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
    """
    Функция "print_hotels" нужна для:
    1. Вывода информации и фото (при необходимости) отеля.
    2. Записи информации о пользователе и отеле в БД.
    """
    parse_list = api.get_hotels_list(message)
    hotels = api.process_hotels_list(parse_list, message)
    if len(hotels) > 0:
        bot.delete_message(message.chat.id, message.message_id + 1)
        bot.send_message(message.from_user.id, text='Результаты поиска:')
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            req_uid = db.add_req(message.from_user.id, data['datetime'], data['commands'], data['city_name'])
            for hotel in hotels:
                db.add_hotels(req_uid, hotel[1], f'https://www.hotels.com/ho{hotel[0]}')
                text = f"🏨 Название отеля: {hotel[1]}" \
                       f"\n🌐 Сайт: https://www.hotels.com/ho{hotel[0]}" \
                       f"\n🌎 Адрес: {hotel[2]}" \
                       f"\n📌 Открыть в Google maps: http://maps.google.com/maps?z=12&t=m&q=loc:{hotel[8]}" \
                       f"\n↔ Расстояние от центра: {hotel[3]} " \
                       f"\n1️⃣ Цена за сутки: {hotel[4]} RUB" \
                       f"\n💳 Цена за период ({hotel[9].days} дн.): {hotel[5]} RUB" \
                       f"\n⭐ Рейтинг: {hotel[6]}" \
                       f"\n✨ Рейтинг по мнению посетителей: {hotel[7]}"
                if data['photos_amt'] > 0:
                    photos = api.request_photo(id_hotel=hotel[0], message=message)
                    try:
                        media = form_media_group(photos=photos, text=text)
                        bot.send_media_group(chat_id=message.chat.id, media=media)
                    except TypeError:
                        bot.send_message(chat_id=message.chat.id, text='📷 Фото данного отеля не найдены\n' + text,
                                         disable_web_page_preview=True)
                else:
                    bot.send_message(chat_id=message.chat.id, text=text, disable_web_page_preview=True)
            logger.info('Вся информация об отелях выведена успешно!')
    else:
        bot.send_message(message.from_user.id, text='Произошла ошибка, повторите попытку.')


@bot.message_handler(commands=['lowprice', 'highprice', 'bestdeal'])
def start(message: Message) -> None:
    """
    Функция "start" нужна для:
    1. Обработки команд '/lowprice', '/highprice' и /bestdeal'.
    2. Запись в состояния время выбранной команды.
    3. Начинает опрос пользователя.
    4. Создание поля в БД.
    """
    bot.set_state(message.from_user.id, UserInfoState.commands, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text == '/lowprice':
            data['commands'] = 'lowprice'
            logger.info('Выбрана команда - lowprice')
        elif message.text == '/highprice':
            data['commands'] = 'highprice'
            logger.info('Выбрана команда - highprice')
        elif message.text == '/bestdeal':
            data['commands'] = 'bestdeal'
            logger.info('Выбрана команда - bestdeal')
        data['datetime'] = datetime.datetime.today()
        logger.info(f"Время команды: {data['datetime']}")
    mess = bot.send_message(message.chat.id, 'Какой город вас интересует?')
    db.db_creation()
    bot.register_next_step_handler(message=mess, callback=get_city_name)


def get_city_name(message: Message) -> None:
    """
    Функция "get_city_name" нужна для:
    1. Обработки города пользователя: если город найден в API, то функция отправляет клавиатуру для уточнения города.
    В ином случае функция запрашивает название еще раз.
    """
    user_city = message.text
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": user_city, "locale": "ru_RU"}
    user_response = api.get_request(url=url, headers=c.headers, params=querystring).text
    if json.loads(user_response)["moresuggestions"] > 0:
        bot.set_state(message.from_user.id, UserInfoState.city_name, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:

            data['city_name'] = user_city
            logger.info('ID пользователя: {}'.format(message.from_user.id))
            logger.info('Выбран город: {}'.format(user_city))
        bot.send_message(message.from_user.id, 'Уточните, пожалуйста:', reply_markup=city_markup(user_response))
    else:
        bot.send_message(message.from_user.id, text='Данный город не найден!')
        start(message)
