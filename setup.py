# Скрипт телеграм-бота
import telebot
import os
import sqlite3
from math import radians, cos, sin, asin, sqrt
from telebot import types
import re
import requests
from telebot.types import InputMediaPhoto
from telebot.util import smart_split
import json

token = '5956727962:AAGSgXUA46pabNdijMqrGJqYtWbFjhZgjrA'
bot = telebot.TeleBot(token)


@bot.message_handler(commands=['start'])
def command_start_handler(message):
    cid = message.chat.id
    bot.send_chat_action(cid, 'typing')
    start_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True, selective=True)
    button_geo = types.KeyboardButton(text='Отправить геолокацию', request_location=True)
    start_markup.add(button_geo)
    bot.send_message(cid, 'Привет, данный бот используется для получения информации о ближайших архитектурных памятниках. \n\n Отправьте, пожалуйста, геолокацию 2 раза, это позволяет боту более точно вычислять расстояния.',
                     reply_markup=start_markup)



def haversine(lon1, lat1, lon2, lat2):

    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def get_distance(long0, lat0, long1, lat1):
    point1 = {"lat":lat0, "lon":long0}
    point2 = {"lat":lat1, "lon":long1}

    url = f"""http://router.project-osrm.org/route/v1/foot/{point1["lat"]},{point1["lon"]};{point2["lat"]},{point2["lon"]}?overview=false&alternatives=false"""
    r = requests.get(url)

    route = json.loads(r.content)["routes"][0]
    return round(route["distance"]/1000, 4)


@bot.message_handler(content_types=['location'])
def get_loc(message):
    long0 = message.location.longitude
    lat0 = message.location.latitude
    bot.register_next_step_handler(message, quant_build, lat0, long0)


def quant_build(message, lat, long):
    bot.send_chat_action(message.chat.id, 'typing')
    markup = types.ReplyKeyboardMarkup(row_width=4, resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton(text='1')
    btn2 = types.KeyboardButton(text='3')
    btn3 = types.KeyboardButton(text='5')
    btn4 = types.KeyboardButton(text='10')
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, 'Выберите количество выводимых зданий (1 - ближайшее, 10 - 10 ближайших)',
                     reply_markup=markup)
    bot.register_next_step_handler(message, get_info, lat, long)

@bot.message_handler(content_types=['text'])
def get_info(message, lat, long):

    bot.send_message(message.chat.id, 'Информация принята. Пожалуйста, подождите. Загрузка изображений требует существенного количества времени (2-3 минуты).')
    quantity = int(message.text)
    with sqlite3.connect('houses1.db') as connection:
        cursor = connection.cursor()
        connection.create_function('haversine', 4, haversine)
        sql = f'''SELECT name, address, text_info, photos, haversine(longitude, latitude, {long}, {lat}) AS distance, longitude, latitude, yearsOfConstruction FROM main ORDER BY distance LIMIT 50'''
        cursor.execute(sql)
        results = cursor.fetchall()

        # Пересчет расстояний по местности
        new_results = []
        for result in results:
            new_results.append([result, get_distance(long, lat, result[5], result[6])])

        new_results = sorted(new_results, key=lambda x: x[1])[:quantity]

        for num, row in enumerate(new_results):

            name = row[0][0]
            address = row[0][1]
            dist = int(round(new_results[num][1], 3) * 1000)

            # Из-за этого фрагмента есть небольшая задержка, но он устраним, если поработать с БД (я забил)
            text_info = re.sub('<[^>]*>', '', row[0][2])
            text_info = re.sub('&nbsp;', '', text_info)
            text_info = re.sub("^\s+|\n|\s+$", '', text_info)
            photos = row[0][3].split("'")

            if row[0][7] == 'None':
                info = f''' \t <ins>Название</ins>: <b>{name}</b> \n \n <ins>Расстояние до здания</ins>: {dist}м \n \n <ins>Информация</ins>:\n \t  {text_info} \n \n \t <b>Адрес</b>: <i>{address}</i>'''
            else:
                info = f''' \t <ins>Название</ins>: <b>{name}</b> \n \n <ins>Расстояние до здания</ins>: {dist}м \n \n <ins>Годы постройки</ins>: {row[0][7]} \n \n <ins>Информация</ins>:\n \t  {text_info} \n \n \t <b>Адрес</b>: <i>{address}</i>'''

            # Выборка ссылок на фотографии из исходного файла (для ускорения этой части надо поработать с БД)
            media_group = []
            for photo in range(1, len(photos), 2):
                r = requests.get(photos[photo])
                media_group.append(r.content)
                if len(media_group) >= 10:
                    break

            bot.send_media_group(message.chat.id, [InputMediaPhoto(x) for x in media_group], disable_notification=True)
            for mes in smart_split(info):
                bot.send_message(message.chat.id, mes, parse_mode='HTML')
            bot.send_location(message.chat.id, longitude=row[0][5], latitude=row[0][6])

    end_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, selective=True)
    btn1 = types.KeyboardButton(text='Отправить геолокацию', request_location=True)
    end_markup.add(btn1)
    bot.send_message(message.chat.id, '''Если вы изменили местоположение или хотите изменить количество выводимых зданий отправьте геолокацию заново (2 раза)''',
                     reply_markup=end_markup)





if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
