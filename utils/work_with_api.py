import json

import requests
from requests import Response
from loguru import logger
from loader import bot


def get_request(url: str, headers: str, params: {}) -> Response:
    """Функция для выполнения запроса"""
    try:
        return requests.get(url=url, headers=headers, params=params, timeout=30)
    except requests.exceptions.RequestException as exc:
        logger.exception(exc)

#
# def get_parse_list(message):
#     with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
#         url = "https://hotels4.p.rapidapi.com/properties/list"
#
#         querystring = {"destinationId": data['hotel_id'], "pageNumber": "1", "pageSize": "25", "checkIn": data['check_in'],
#                        "checkOut": data['check_out'], "adults1": "1", "sortOrder": "PRICE", "locale": "ru_RU", "currency": "RUB"}
#
#         headers = {
#             "X-RapidAPI-Key": "375795fc0bmsh97f30b2af4e08ebp183724jsnc26554dd3feb",
#             "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
#         }
#
#         req = get_request(url=url, headers=headers, params=querystring)
#         parse_list = json.loads(req.text)
#         return parse_list
#
#
# def parse_list(parse_list: list, message, distance: str = '') -> list:
#     """Функция для подготовки данных к записи в бд"""
#     hotels = []
#     hotel_id, name, address, center, price = '', '', '', 'нет данных', ''
#
#     for hotel in parse_list:
#         try:
#             with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
#                 hotel_id = int(hotel['id'])
#                 name = hotel['name']
#                 address = f'{hotel["address"]["countryName"]}, {data["city_name"].capitalize()}, {hotel["address"].get("postalCode", "")}, {hotel["address"].get("streetAddress", "")}'
#                 if len(hotel['landmarks']) > 0:
#                     if hotel['landmarks'][0]['label'] == 'Центр города':
#                         center = hotel['landmarks'][0]['distance']
#                 price = str(hotel['ratePlan']['price']['exactCurrent'])
#                 coordinates = f"{hotel['coordinate'].get('lat', 0)},{hotel['coordinate'].get('lon', 0)}"
#                 star_rating = str(hotel['starRating'])
#                 user_rating = hotel.get('guestReviews', {}).get('rating', 'нет данных').replace(',', '.')
#                 if distance != '':
#                     if float(distance) < float(center.split()[0].replace(',', '.')):
#                         return hotels
#                 hotels.append((hotel_id, name, address, center, price, coordinates, star_rating, user_rating))
#         except (LookupError, ValueError) as exc:
#             logger.exception(exc)
#             continue
#     return hotels
