import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, IntegrityError

from subscriptions import util


class City(models.Model):
    name = models.CharField(max_length=200)
    state = models.CharField(max_length=2, choices=util.STATES)
    population = models.IntegerField()
    time_zone = models.CharField(max_length=200)

    class Meta:
        unique_together = ('name', 'state')

    def __str__(self):
        return '%s, %s' % (self.name, self.state)


class Subscription(models.Model):
    email = models.EmailField(db_index=True)
    subscribed = models.BooleanField(
        default=True, verbose_name='subscribed', db_index=True
    )
    date_subscribed = models.DateTimeField(
        verbose_name='subscribe date', auto_now_add=True
    )
    date_unsubscribed = models.DateTimeField(
        verbose_name='unsubscribe date', blank=True, null=True
    )
    newsletter = models.CharField(max_length=2, choices=util.NEWSLETTERS)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('email', 'newsletter')

    @classmethod
    def subscribe(cls, email, newsletter, city):
        '''
        Create a new subscription
        If subscription exists:
        - subscribe back if unsubscribed
        - update the city

        @raises   - django.db.IntegrityError if trying to duplicate when
                    subscribed

        This way email - subscription combination is unique.
        '''
        obj = cls.objects.filter(email=email, newsletter=newsletter).first()
        if obj is None:
            updated = False
            obj = cls(email=email, newsletter=newsletter, city=city)
        else:
            if obj.subscribed and obj.city == city:
                raise IntegrityError(
                    'Combination of %s, %s, %s already exists' % (
                        email, newsletter, city)
                )
            obj.city = city
            obj.subscribed = True
            updated = True
        obj.save()
        return (obj, updated)

    @classmethod
    def unsubscribe(cls, email, newsletter):
        '''
        Unsubscribe an email from a newsletter.
        Note that this does not delete the record. Only subscribed is
        switched to false
        '''
        obj = cls.objects.filter(email=email, newsletter=newsletter).first()
        if obj is None:
            raise ObjectDoesNotExist()

        obj.subscribed = False
        obj.date_unsubscribed = datetime.datetime.now()
        obj.save()


class Event(models.Model):
    subscriber = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    sender = models.EmailField(db_index=True)
    date_sent = models.DateTimeField(
        auto_now_add=True, verbose_name='date email was sent')
    newsletter = models.CharField(max_length=2, choices=util.NEWSLETTERS)
    subject = models.CharField(max_length=998)
