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


def calculate_delivery_distance(places, start_point, end_points_list):
    points_with_distance = []

    try:
        client_coordinates = places.get(
            address=start_point
        )
    except Place.DoesNotExist:
        coordinates = fetch_coordinates(
            apikey=settings.YANDEX_API_KEY,
            address=start_point,
        )

        client_coordinates = Place.objects.create(
            address=start_point,
            lon=coordinates[0],
            lat=coordinates[1],
        ) if coordinates else None

    for point in end_points_list:
        try:
            restaurant_coordinates = places.get(
                address=point.address
            )
        except Place.DoesNotExist:
            coordinates = fetch_coordinates(
                apikey=settings.YANDEX_API_KEY,
                address=point.address,
            )

            restaurant_coordinates = Place.objects.create(
                address=point.address,
                lon=coordinates[0],
                lat=coordinates[1],
            ) if coordinates else None

        if restaurant_coordinates is None or client_coordinates is None:
            delivery_distance = 'Адрес не определен'
        else:
            delivery_distance = round(distance.distance(
                (restaurant_coordinates.lat, restaurant_coordinates.lon),
                (client_coordinates.lat, client_coordinates.lon),
            ).km, 2)

        points_with_distance.append(
            (point.name, delivery_distance)
        )

    return points_with_distance
