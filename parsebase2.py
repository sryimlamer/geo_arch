# parse2
import requests
import json
import sqlite3


def get_json(slug):

    params = {
        'slug': slug,
    }
    response = requests.get(
        'https://um.mos.ru/_next/data/OOf9NAVaJjEDoBN1mri5m/ru/houses/' + slug + '.json',
        params=params
    )
    print('https://um.mos.ru/_next/data/OOf9NAVaJjEDoBN1mri5m/ru/houses/' + slug + '.json')

    return response.json()


def parse_json(db):
    with sqlite3.connect('houses.db') as connection:
        cursor = connection.cursor()
        items = []

        # Получили необходимые данные
        for item in db:
            house = {}
            slug = item['slug']
            print(slug)
            house['slug'] = slug
            house['coordinates'] = item['coordinates']
            if len(house['coordinates']) != 0:
                lat = house['coordinates'][0]
                long = house['coordinates'][1]
            else:
                lat = 0
                long = 0
            house['name'] = item['name']
            house['address'] = item['address']
            house['yearsOfConstruction'] = item['yearsOfConstruction']

            # Догружаем данные через запросы к каждому объекту
            raw_build_inf = get_json(slug)
            if raw_build_inf is None:
                continue
            building = raw_build_inf['pageProps']['initialState']['items']['item']

            try:
                building['categories'][0]['children'][0]['name']  # Категория десятилетие
            except IndexError:
                house['categ_years'] = None
            else:
                house['categ_years'] = building['categories'][0]['children'][0]['name']

            if len(building['textBlocks']) != 0:
                house['text_info'] = building['textBlocks'][0]['textText']
            else:
                house['text_info'] = ''

            # Фото
            photos = []
            try:
                building['mediaFiles']['images']
            except KeyError:
                photos = None
            else:
                for photo in building['mediaFiles']['images']:
                    ph = 'https://um.mos.ru' + photo['file']
                    #                     ph['title'] = photo['title']
                    photos.append(ph)

            house['photos'] = photos

            items.append(house)

            # Экранирование всего
            house['slug'] = house['slug'].replace('\'', '"')
            house['name'] = house['name'].replace('\'', '"')
            if house['yearsOfConstruction'] is not None:
                house['yearsOfConstruction'] = house['yearsOfConstruction'].replace('\'', '"')
            if house['address'] is not None:
                house['address'] = house['address'].replace('\'', '"')
            house['text_info'] = house['text_info'].replace('\'', '"')

            sql = f'''INSERT INTO main(slug, name, address, yearsOfConstruction, text_info, photos, latitude, 
            longitude) VALUES('{slug}', '{house['name']}', '{house['address']}', '{house['yearsOfConstruction']}', '{house['text_info']}', "{house['photos']}", '{lat}', '{long}')'''
            cursor.execute(sql)
            connection.commit()

    return items


def parse_uznai(place, pages):
    all_places = []

    # Проходим по контенту каждой страницы
    for page in range(1, pages):
        print(page)
        url = 'https://um.mos.ru/api/v1/' + place + '?page=' + str(page)
        r = requests.get(url)
        places = r.json()
        db = places['result']

        all_places.extend(parse_json(db))
    return all_places


our_json = parse_uznai('houses', 187)

with open('houses.json', 'w') as outfile:
    json.dump(our_json, outfile, ensure_ascii=False)