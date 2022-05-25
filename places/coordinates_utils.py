import requests
from geopy import distance
from django.conf import settings

from places.models import Place


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def save_new_place_to_db(address):
    coordinates = fetch_coordinates(
        apikey=settings.YANDEX_API_KEY,
        address=address,
    )

    new_place = Place.objects.create(
        address=address,
        lon=coordinates[0],
        lat=coordinates[1],
    ) if coordinates else None

    return new_place


def calculate_delivery_distance(places_query_set, start_point, end_points_list):
    points_with_distance = []
    end_points_addresses = [end_point.address for end_point in end_points_list]
    client_coordinates = None
    restaurants = []

    for place in places_query_set:
        if start_point == place.address:
            client_coordinates = place

        if place.address in end_points_addresses:
            for end_point in end_points_list:
                if end_point.address == place.address:
                    restaurants.append((end_point.name, place))
                    end_points_list.remove(end_point)

    if not client_coordinates:
        client_coordinates = save_new_place_to_db(start_point)

    if end_points_list:
        for end_point in end_points_list:
            new_place = save_new_place_to_db(end_point.address)
            restaurants.append((end_point.name, new_place))

    for restaurant_name, coordinates in restaurants:
        if coordinates is None or client_coordinates is None:
            delivery_distance = 'Адрес не определен'
        else:
            delivery_distance = round(distance.distance(
                (coordinates.lat, coordinates.lon),
                (client_coordinates.lat, client_coordinates.lon),
            ).km, 2)

        points_with_distance.append(
            (restaurant_name, delivery_distance)
        )

    return points_with_distance
