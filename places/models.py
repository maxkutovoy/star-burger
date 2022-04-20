from django.db import models
from django.utils import timezone


class Place(models.Model):
    address = models.CharField(
        'адрес',
        unique=True,
        max_length=200,
    )

    lat = models.FloatField(
        'широта',
        blank=True,
        null=True,
    )

    lon = models.FloatField(
        'долгота',
        blank=True,
        null=True,
    )

    created = models.DateTimeField(
        'дата создания',
        default=timezone.now,
    )

    class Meta:
        verbose_name = 'место'
        verbose_name_plural = 'места'

    def __str__(self):
        return self.address
