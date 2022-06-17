import telebot

if __name__ == '__main__':
    bot = telebot.TeleBot('5360344539:AAHmp4MnK8DQFMHgHE0TBWySTRiA9mHNcZQ')


    @bot.message_handler(content_types=['text'])
    def get_text_messages(message):
        if message.text == '/hello-world':
            bot.send_message(message.from_user.id, 'Привет мир!')
        elif message.text == 'Привет':
            mess = 'Привет {} {}'.format(message.from_user.first_name, message.from_user.last_name)
            bot.send_message(message.from_user.id, mess)
        elif message.text == '/help':
            bot.send_message(message.from_user.id, 'У меня есть команда /hello-world')
        else:
            bot.send_message(message.from_user.id, 'Я тебя не понимаю. Напиши /help.')


    bot.polling(none_stop=True, interval=0)
