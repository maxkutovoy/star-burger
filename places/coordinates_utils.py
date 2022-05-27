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
    found_places = response.json()['response']['GeoObjectCollection'][
        'featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def save_new_place_to_db(address, coordinates):
    new_place = Place.objects.create(
        address=address,
        lat=coordinates[0],
        lon=coordinates[1],
    ) if coordinates else None

    return new_place


def calculate_delivery_distance(order_coordinates_by_addresses,
                                restaurant_coordinates_by_addresses,
                                start_point, end_points):
    points_with_distance = []
    restaurants = []

    if start_point in order_coordinates_by_addresses.keys():
        order_coordinates = order_coordinates_by_addresses[start_point]
    else:
        order_coordinates = fetch_coordinates(
            settings.YANDEX_API_KEY, start_point)
        if order_coordinates:
            save_new_place_to_db(start_point, order_coordinates)

    for end_point in end_points:
        if end_point.address in restaurant_coordinates_by_addresses.keys():
            end_point_coordinates = restaurant_coordinates_by_addresses[
                end_point.address]
        else:
            end_point_coordinates = fetch_coordinates(
                settings.YANDEX_API_KEY, end_point.address)
            if end_point_coordinates:
                save_new_place_to_db(end_point.address, end_point_coordinates)

        restaurants.append((end_point.name, end_point_coordinates))

    for restaurant_name, coordinates in restaurants:
        if order_coordinates is None or end_point_coordinates is None:
            delivery_distance = 'Адрес не определен'
        else:
            delivery_distance = round(distance.distance(
                (end_point_coordinates[0], end_point_coordinates[1]),
                (order_coordinates[0], order_coordinates[1]),
            ).km, 2)

        points_with_distance.append(
            (restaurant_name, delivery_distance)
        )

    return points_with_distance
