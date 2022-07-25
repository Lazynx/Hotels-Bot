from loader import bot
from config_data import config as c

import json
import requests

from loguru import logger

from json import JSONDecodeError
from requests import Response
from telebot.types import Message
from typing import Dict


def get_request(url: str, headers: str, params: Dict) -> Response:
    """
    Функция "get_request" выполняет запрос.
    :param url: ссылка запроса
    :param headers: Заголовки запроса
    :param params: Параметры запроса
    :return: Запрос по указанным параметрам
    """
    return requests.get(url=url, headers=headers, params=params, timeout=30)


def get_hotels_list(message: Message) -> list:
    """
    Функция "get_hotels_list" создает список отелей по ID города.
    :param message: Сообщение пользователя
    :return: Список отелей из API
    """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        url = "https://hotels4.p.rapidapi.com/properties/list"
        min_price = ''
        max_price = ''
        if data['commands'] == 'lowprice':
            sort_method = "PRICE"
        elif data['commands'] == 'highprice':
            sort_method = "PRICE_HIGHEST_FIRST"
        elif data['commands'] == 'bestdeal':
            sort_method = "DISTANCE_FROM_LANDMARK"
            min_price = data['min_price']
            max_price = data['max_price']
    landmarkIds = 'Центр города'
    querystring = {"destinationId": data['city_id'], "pageNumber": "1", "pageSize": "25",
                   "checkIn": data['check_in'], "checkOut": data['check_out'], "adults1": "1", "priceMin": min_price,
                   "priceMax": max_price, "sortOrder": sort_method, "locale": "ru_RU", "currency": "RUB",
                   "landmarkIds": landmarkIds}
    req = get_request(url=url, headers=c.headers, params=querystring)
    parse_list = json.loads(req.text)
    return parse_list


def process_hotels_list(parse_list: list, message: Message) -> list:
    """
    Функция "process_hotels_list" формирует данные об отеле.
    :param parse_list: Список отелей
    :param message: Сообщение пользователя
    :return: Сформированный список отелей
    """
    hotels = []
    hotel_id, name, address, center, night_price, full_price = '', '', '', 'нет данных', '', ''
    hot_cnt = 0

    for hotel in parse_list["data"]["body"]["searchResults"]["results"]:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            if hot_cnt < data['hotels_amt']:
                hotel_id = hotel["id"]
                name = hotel["name"]
                address = f'{hotel["address"]["countryName"]}, {hotel["address"]["locality"]}, ' \
                          f'{hotel["address"].get("postalCode", "")}, {hotel["address"].get("streetAddress", "")}'
                if len(hotel['landmarks']) > 0:
                    if hotel['landmarks'][0]['label'] == 'Центр города':
                        if data['commands'] == 'bestdeal':
                            hot_dist = (hotel['landmarks'][0]['distance']).replace(',', '.')
                            if float(hot_dist.replace(' км', '')) <= data['distance']:
                                center = hotel['landmarks'][0]['distance']
                            else:
                                continue
                        else:
                            center = hotel['landmarks'][0]['distance']
                night_price = str(round(hotel['ratePlan']['price']['exactCurrent']))
                period = data['check_out'] - data['check_in']
                full_price = str(round(int(night_price) * period.days))
                star_rating = str(hotel['starRating'])
                coordinates = f"{hotel['coordinate'].get('lat', 0)},{hotel['coordinate'].get('lon', 0)}"
                user_star_rating = hotel.get('guestReviews', {}).get('rating', 'нет данных').replace(',', '.')
                hotels.append((hotel_id, name, address, center, night_price, full_price, star_rating,
                               user_star_rating, coordinates, period))
                hot_cnt += 1
            else:
                break
    return hotels


def request_photo(id_hotel: str, message: Message) -> list:
    """
    Функция "request_photo" делает запрос к API и получает данные о фотографиях.
    :param id_hotel: ID отеля
    :param message: Сообщение пользователя
    :return: Список фото
    """
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": id_hotel}
    photos = []
    try:
        response = get_request(url=url, headers=c.headers, params=querystring)
        ph_data = json.loads(response.text)
        ph_cnt = 0
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            for photo in ph_data['hotelImages']:
                if ph_cnt < data['photos_amt']:
                    ph_cnt += 1
                    url = photo['baseUrl'].replace('_{size}', '_z')
                    photos.append((id_hotel, url))
                else:
                    break
        return photos
    except (JSONDecodeError, TypeError) as exc:
        logger.exception(exc)


def check_foto(photo: str) -> bool:
    """
    Функция "check_foto" проверяет URL фото.
    :param photo: Ссылка на фото
    :return: Булево значение
    """
    try:
        checking_foto = requests.get(url=photo, timeout=20)
        if checking_foto.status_code == 200:
            return True
    except requests.exceptions.RequestException as exc:
        logger.exception(exc)
