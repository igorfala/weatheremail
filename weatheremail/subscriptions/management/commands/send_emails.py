#!/usr/bin/env python3
import asyncio

import aiohttp
import django

import subscriptions
# insert BASE_DIR in PATH so we can import apis.wunderground
import sys
sys.path.insert(0, django.conf.settings.BASE_DIR)
import apis.wunderground # noqa E402


class Command(django.core.management.base.BaseCommand):
    help = ('Send bulk emails to all the subscribers of a newsletter')
    sent = 0
    cities = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-limit',
            '-l',
            dest='api_limit',
            default=10,
            help='API call limit per minute',
        )
        parser.add_argument(
            '--newsletter',
            '-n',
            dest='newsletter',
            default='WD',
            help='Newsletter to whose subscribers to send email',
        )

    async def _send_bulk(self, newsletter, api_limit, verbosity):
        async with aiohttp.ClientSession() as session:
            subscribers = subscriptions.models.Subscription.objects.filter(
                subscribed=True).filter(newsletter=newsletter)
            subscr_cities = {}
            for subscr in subscribers:
                key = (subscr.city.name, subscr.city.state)
                if key not in subscr_cities:
                    subscr_cities[key] = []
                subscr_cities[key].append(subscr)
            wuclient = apis.wunderground.Client(
                key=django.conf.settings.WUNDERGROUND_KEY,
                session=session,
            )
            for i, k in enumerate(subscr_cities):
                city, state = k
                conditions = await wuclient.get(
                    feature='conditions',
                    query={'city': city, 'state': state},
                )
                today = conditions['current_observation']
                almanac = await wuclient.get(
                    feature='almanac',
                    query={'city': city, 'state': state},
                )

                def average(almanac):
                    almanac = almanac['almanac']
                    avg_high = float(almanac['temp_high']['normal']['F'])
                    avg_low = float(almanac['temp_low']['normal']['F'])
                    return (avg_low + avg_high) / 2

                def subject():
                    avg = average(almanac)
                    feelslike_f = float(today['feelslike_f'])
                    weather = today['weather'].lower()
                    if (weather in ('overcast', 'rain')
                            or avg - feelslike_f >= 5):
                        return ('Not so nice out? That\'s okay, enjoy a '
                            'discount on us.')
                    if (weather == 'clear'
                            or feelslike_f - avg >= 5):
                        return 'It\'s nice out! Enjoy a discount on us.'
                    return 'Enjoy a discount on us'

                self.cities += 1
                subject = subject()
                with django.core.mail.get_connection() as connection:
                    for subscriber in subscr_cities[k]:
                        data = {'today': today}
                        html = django.template.loader.render_to_string(
                            'weather_discount_email.html',
                            data,
                        )
                        email = django.core.mail.EmailMessage(
                            subject=subject,
                            body=html,
                            from_email=django.conf.settings.DEFAULT_FROM_EMAIL,
                            to=[subscriber.email],
                            connection=connection,
                        )
                        email.content_subtype = 'html'
                        email.send()
                        subscriptions.models.Event(
                            subscriber=subscriber,
                            sender=django.conf.settings.DEFAULT_FROM_EMAIL,
                            newsletter=newsletter,
                            subject=subject,
                        ).save()
                        if verbosity:
                            print('Email sent to <%s>, with subject: %s' % (
                                subscriber.email, subject)
                            )

                        self.sent += 1

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self._send_bulk(
                newsletter=options['newsletter'],
                api_limit=options['api_limit'],
                verbosity=options['verbosity']),
            )
        except KeyboardInterrupt:
            pass
        finally:
            print(
                '\nShutting down asyncio event loop.',
                '\nSent %i emails' % (self.sent,),
                '\nGot weather for %i cities' % (self.cities,),
                '\nMade %i calls to wunderground API' % (self.cities * 2,)
            )
