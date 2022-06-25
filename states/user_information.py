from telebot.handler_backends import State, StatesGroup


class UserInfoState(StatesGroup):
    city_name = State()
    city_id = State()
    hotels_amt = State()
    uploading_photos = State()
    photos_amt = State()
    check_in = State()
    check_out = State()
    min_price_for_night = State()
    max_price_for_night = State()
    min_distance_to_centre = State()
    max_distance_to_centre = State()