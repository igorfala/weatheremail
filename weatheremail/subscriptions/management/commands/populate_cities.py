#!/usr/bin/env python3

import asyncio
import json

import aiohttp
import django
import googlemaps

import subscriptions


class Command(django.core.management.base.BaseCommand):
    help = ('Populate table subscription_city with 1000 most populated cities'
        ' in US.')
    counter = 0
    inserted = 0

    async def _populate(self, verbosity):
        gclient = googlemaps.Client(key=django.conf.settings.GOOGLE_KEY)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url=('https://gist.githubusercontent.com/Miserlou/'
                'c5cd8364bf9b2420bb29/raw/2bf258763cdddd704f8ffd3'
                'ea9a3e81d25e2c6f6/cities.json')
            ) as resp:
                # Even though the resp format is json, since the
                # headers[''Content-Type'] == 'text/plain; charset=utf-8'
                # aiohttp does not recognize it as valid json, so reading text
                # and getting json from it
                cities = json.loads(await resp.text())
        for i, city in enumerate(cities):
            # Pause every 100 requests to not hammer on the API and DB
            if i > 0 and i % 100 == 0:
                if verbosity:
                    print('Delaying requests for 3 seconds')
                await asyncio.sleep(3)

            state = subscriptions.util.STATES_MAP[city['state'].upper()]
            # One of the table constraints is that the combination
            # City, State is unique. If that combination doesn't exist,
            # insert it
            if subscriptions.models.City.objects.filter(
                    name__iexact=city['city'],
                    state__iexact=state):
                if verbosity:
                    print('%s : already exists. Ignore' % (city['city'],))
            else:
                time_zone = gclient.timezone(
                    location=(city['latitude'], city['longitude'])
                )['timeZoneId']
                subscriptions.models.City(
                    name=city['city'],
                    state=state,
                    population=city['population'],
                    time_zone=time_zone,
                ).save()
                if verbosity:
                    print('Insert: %s, %s' % (city['city'], state))
                self.inserted += 1
            self.counter += 1

    def handle(self, *args, **options):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                self._populate(verbosity=options['verbosity']))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(e)
        finally:
            print(
                '\nShutting down asyncio event loop.',
                '\nProcessed %i cities' % (self.counter,),
                '\nInserted %i in the DB' % (self.inserted,)
            )
