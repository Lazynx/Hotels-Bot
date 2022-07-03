from peewee import *
from loguru import logger
import datetime

db = SqliteDatabase('history.db')


class BaseModel(Model):
    class Meta:
        database = db


class UserRequest(BaseModel):
    """ Класс таблицы запроса пользователя. """
    request_uid = IntegerField(primary_key=True)
    telegram_id = IntegerField()
    date = DateTimeField()
    command = CharField()
    city_name = CharField()


class Hotels(BaseModel):
    """ Класс таблицы отелей. """
    hotels_uid = IntegerField(primary_key=True)
    request_uid = IntegerField(index=True)
    hotel_name = CharField()
    hotel_url = CharField()


def add_req(user_id: int, user_date: datetime, user_command: str, user_city_name: str) -> int:
    """
    Функция "add_req" записывает информацию в поля таблицы запросов пользователя.
    :param user_id: ID пользователя
    :param user_date: дата команды
    :param user_command: команда пользователя
    :param user_city_name: название города
    :return: uid запроса пользователя
    """
    with db:
        uid = UserRequest.create(telegram_id=user_id, date=user_date, command=user_command, city_name=user_city_name)
    return uid


def add_hotels(req_uid: int, hotel_name: str, hotel_url: str) -> None:
    """
    Функция "add_hotels" записывает информацию в поля таблицы отелей.
    :param req_uid: uid запроса
    :param hotel_name: название отеля
    :param hotel_url: ссылка на отель
    """
    with db:
        Hotels.create(request_uid=req_uid, hotel_name=hotel_name, hotel_url=hotel_url)


def db_creation() -> None:
    """ Функция "db_creation", создает таблицы с запросом пользователя и отелями.  """
    with db:
        if not UserRequest.table_exists():
            UserRequest.create_table()
            Hotels.create_table()


def get_info_from_db(user_id: int) -> list:
    """
    Функция "get_info_from_db" нужна для:
    Получения информации из БД по ID пользователя.
    :param user_id: ID пользователя
    :return: Список с историей пользователя.
    """
    with db:
        req_list = list()
        for i_req in UserRequest.select().where(UserRequest.telegram_id == user_id).order_by(UserRequest.date.desc())\
                .limit(5):
            hotels_list = list()
            for i_hotels in Hotels.select().where(Hotels.request_uid == i_req.request_uid):
                hotels_list.append((i_hotels.hotel_name, i_hotels.hotel_url))
            req_list.append((i_req.date, i_req.command, i_req.city_name, hotels_list))
    return req_list
