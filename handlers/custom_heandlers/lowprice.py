from loader import bot

import json
import re

from loguru import logger
from states.user_information import UserInfoState
from utils import work_with_api
from telegram_bot_calendar import WYearTelegramCalendar, LSTEP
import datetime

from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from typing import List


class MyStyleCalendar(WYearTelegramCalendar):
    prev_button = "⬅️"
    next_button = "➡️"
    empty_month_button = ""
    empty_year_button = ""


def city_founding(response) -> List:
    pattern = r'(?<="CITY_GROUP",).+?[\]]'
    find = re.search(pattern, response)
    if find:
        suggestions = json.loads(f"{{{find[0]}}}")
    cities = list()
    for dest_id in suggestions['entities']:  # Обрабатываем результат
        clear_destination = re.sub(r"<span class='highlighted'>(.*)</span>", r'\1', dest_id['caption'])
        if re.search(r"</span>.<span class='highlighted'>", clear_destination):
            full_clear_destination = re.sub(r"</span>.<span class='highlighted'>", ' ', clear_destination)
            cities.append({'city_name': full_clear_destination, 'destination_id': dest_id['destinationId']})
        else:
            cities.append({'city_name': clear_destination, 'destination_id': dest_id['destinationId']})
    return cities


def city_markup(message: Message) -> InlineKeyboardMarkup:
    cities = city_founding(message)
    # Функция "city_founding" уже возвращает список словарей с нужным именем и id
    destinations = InlineKeyboardMarkup()
    for i_city in cities:
        destinations.add(InlineKeyboardButton(text=i_city['city_name'],
                                              callback_data=f'{i_city["destination_id"]}'))

    return destinations


LSTEP = {'y': 'год', 'm': 'месяц', 'd': 'день'}


@bot.callback_query_handler(func=lambda call: call.data.isdigit())
def get_city_id(call: CallbackQuery) -> None:
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
        bot.send_message(call.from_user.id, f"Выберите {LSTEP[step]}", reply_markup=calendar)


def get_calendar(is_process=False, callback_data=None, **kwargs):
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
def get_check_in(call: CallbackQuery):
    today = datetime.date.today()
    result, key, step = get_calendar(calendar_id=1,
                                     current_date=today,
                                     min_date=today,
                                     max_date=today + datetime.timedelta(days=365),
                                     locale="ru",
                                     is_process=True,
                                     callback_data=call)
    if not result and key:
        # Продолжаем отсылать шаги, пока не выберут дату "result"
        bot.edit_message_text(f"Выберите {LSTEP[step]}",
                              call.from_user.id,
                              call.message.message_id,
                              reply_markup=key)
    elif result:
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            data['check_in'] = result  # Дата выбрана, сохраняем ее
            logger.info('Дата заезда: {}'.format(result))

            bot.delete_message(call.message.chat.id, call.message.message_id - 1)
            bot.edit_message_text(f"Дата заезда {result}",
                                  call.message.chat.id,
                                  call.message.message_id)

            bot.send_message(call.from_user.id, "Выберите дату выезда")
            # И здесь сразу используем вновь полученные данные и генерируем новый календарь
            calendar, step = get_calendar(calendar_id=2,
                                          min_date=result + datetime.timedelta(days=1),
                                          max_date=result + datetime.timedelta(days=365),
                                          locale="ru",
                                          )

            bot.send_message(call.from_user.id,
                             f"Выберите {LSTEP[step]}",
                             reply_markup=calendar)

            bot.set_state(call.from_user.id, UserInfoState.check_out, call.message.chat.id)


@bot.callback_query_handler(func=MyStyleCalendar.func(calendar_id=2))
def get_check_out(call: CallbackQuery):
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        result, key, step = get_calendar(calendar_id=2,
                                         current_date=data['check_in'],
                                         min_date=data['check_in'] + datetime.timedelta(days=1),
                                         max_date=data['check_in'] + datetime.timedelta(days=365),
                                         locale="ru",
                                         is_process=True,
                                         callback_data=call)
        if not result and key:
            bot.edit_message_text(f"Выбери {LSTEP[step]}",
                                  call.from_user.id,
                                  call.message.message_id,
                                  reply_markup=key)

        elif result:
            with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                data['check_out'] = result
                logger.info('Дата выезда: {}'.format(result))
                bot.delete_message(call.message.chat.id, call.message.message_id - 1)

                bot.edit_message_text(f"Дата выезда {result}",
                                      call.message.chat.id,
                                      call.message.message_id)
                bot.send_message(call.from_user.id, text='Введите кол-во отелей\n'
                                                         '(максимум 10):')


@bot.message_handler(state=UserInfoState.check_out)
def get_hotels_amt(message: Message) -> None:
    if message.text.isdigit() and int(message.text) <= 10:
        bot.send_message(message.from_user.id, text='Необходима ли загрузка фото?\n'
                                                    'Да/Нет')
        bot.set_state(message.from_user.id, UserInfoState.hotels_amt, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['hotels_amt'] = int(message.text)
            logger.info('Кол-во отелей: {}'.format(int(message.text)))
    else:
        bot.send_message(message.from_user.id, text='Введено не верное число!')


@bot.message_handler(state=UserInfoState.hotels_amt)
def need_photo(message: Message) -> None:
    if message.text.lower() == 'да':
        bot.send_message(message.from_user.id, text='Хорошо, какое кол-во фото отеля должно быть\n'
                                                    '(не больше 5)?')
        bot.set_state(message.from_user.id, UserInfoState.uploading_photos, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['uploading_photos'] = True
            logger.info('Выбран режим с просмотром фотографий')
    elif message.text.lower() == 'нет':
        bot.set_state(message.from_user.id, UserInfoState.uploading_photos, message.chat.id)
        bot.set_state(message.from_user.id, UserInfoState.photos_amt, message.chat.id)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['uploading_photos'] = False
            data['photos_amt'] = 0
            logger.info('Выбран режим без просмотром фотографий')
        bot.send_message(message.from_user.id, text='Хорошо, начинаю загрузку отелей...')
    else:
        bot.send_message(message.from_user.id, text='Я тебя не понял!')


@bot.message_handler(state=UserInfoState.uploading_photos)
def get_photos_amt(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text.isdigit() and int(message.text) <= 5:
            bot.send_message(message.from_user.id, text='Отлично, начинаю загрузку отелей...')
            bot.set_state(message.from_user.id, UserInfoState.photos_amt, message.chat.id)
            data['photos_amt'] = int(message.text)
            logger.info('Кол-во фото, которое нужно загрузить: {}'.format(int(message.text)))
        else:
            bot.send_message(message.from_user.id, text='Введено не верное число!')


@bot.message_handler(commands=['lowprice'])
def start(message: Message) -> None:
    mess = bot.send_message(message.chat.id, 'Какой город вас интересует?')
    logger.info('Пользователь с айди: {}'.format(message.from_user.id))
    bot.register_next_step_handler(mess, get_city_name)


def get_city_name(message: Message) -> None:
    user_city = message.text
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"
    querystring = {"query": user_city, "locale": "ru_RU"}
    headers = {
        "X-RapidAPI-Key": "375795fc0bmsh97f30b2af4e08ebp183724jsnc26554dd3feb",
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }
    user_response = work_with_api.get_request(url, headers, querystring).text
    if json.loads(user_response)["moresuggestions"] > 0:
        bot.send_message(message.from_user.id, 'Уточните, пожалуйста:', reply_markup=city_markup(user_response))
    else:
        bot.send_message(message.from_user.id, text='Данный город не найден!')
        start(message)

    bot.set_state(message.from_user.id, UserInfoState.city_name, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['city_name'] = user_city
        logger.info('Выбран город: {}'.format(user_city))
