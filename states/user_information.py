from telebot.handler_backends import State, StatesGroup


class UserInfoState(StatesGroup):
    """ Класс состояний пользователя. """
    datetime = State()
    commands = State()
    city_name = State()
    city_id = State()
    hotels_amt = State()
    picture_mode = State()
    photos_amt = State()
    check_in = State()
    check_out = State()
    min_price = State()
    max_price = State()
    distance = State()
