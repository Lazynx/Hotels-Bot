from loader import bot
from config_data import config as c

import json
import requests

from loguru import logger

from json import JSONDecodeError
from requests import Response
from telebot.types import Message


def get_request(url: str, headers: str, params: {}) -> Response:
    """ Функция для выполнения запроса. """
    return requests.get(url=url, headers=headers, params=params, timeout=30)


def get_hotels_list(message: Message) -> list:
    """ Функция для получения списков отелей по ID города. """
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        url = "https://hotels4.p.rapidapi.com/properties/list"

        querystring = {"destinationId": data['city_id'], "pageNumber": "1", "pageSize": "25",
                       "checkIn": data['check_in'],
                       "checkOut": data['check_out'], "adults1": "1", "sortOrder": "PRICE", "locale": "ru_RU",
                       "currency": "RUB"}

        req = get_request(url=url, headers=c.headers, params=querystring)
        parse_list = json.loads(req.text)
        return parse_list


def process_hotels_list(parse_list: list, message: Message) -> list:
    """ Функция для формирования данных об отеле. """
    hotels = []
    hotel_id, name, address, center, night_price, full_price = '', '', '', 'нет данных', '', ''
    hot_cnt = 0

    for hotel in parse_list["data"]["body"]["searchResults"]["results"]:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            if hot_cnt < data['hotels_amt']:
                hot_cnt += 1
                hotel_id = hotel["id"]
                name = hotel["name"]
                address = f'{hotel["address"]["countryName"]}, {hotel["address"]["locality"]}, ' \
                          f'{hotel["address"].get("postalCode", "")}, {hotel["address"].get("streetAddress", "")}'
                if len(hotel['landmarks']) > 0:
                    if hotel['landmarks'][0]['label'] == 'Центр города':
                        center = hotel['landmarks'][0]['distance']
                night_price = str(round(hotel['ratePlan']['price']['exactCurrent']))
                period = data['check_out'] - data['check_in']
                full_price = str(round(int(night_price) * period.days))
                star_rating = str(hotel['starRating'])
                coordinates = f"{hotel['coordinate'].get('lat', 0)},{hotel['coordinate'].get('lon', 0)}"
                hotels.append((hotel_id, name, address, center, night_price, full_price, star_rating,
                               coordinates, period))
            else:
                break
    return hotels


def request_photo(id_hotel: str, message: Message) -> list:
    """ Функция для запроса к API и получения данных о фотографиях. """
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
    """ Функция для проверки URL фото. """
    try:
        checking_foto = requests.get(url=photo, timeout=30)
        if checking_foto.status_code == 200:
            return True
    except requests.exceptions.RequestException as exc:
        logger.exception(exc)
