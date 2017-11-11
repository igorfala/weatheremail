import asyncio
import time

import yarl


class TokenBucket(object):
    def __init__(self, session, limit):
        '''
        Token Bucket API rate limit per minute
        @param session   - aiohttp ClientSession
        @param limit     - api rate limit per minute
        '''
        self._session = session
        # Initially issue as many tokens as the limit is
        self._tokens = self._limit = limit
        self._updated_at = time.monotonic()

    async def api_call(self, method, *args, **kwds):
        '''
        Handler of  client session requests.

        @param method  - http method
        '''
        await self._wait_for_token()
        async with getattr(self._session, method)(*args, **kwds) as api_resp:
            return api_resp

    async def _wait_for_token(self):
        while self._tokens < 1:
            await self._add_new_tokens()
            asyncio.sleep(0.25)
        self._tokens -= 1

    async def _add_new_tokens(self):
        now = time.monotonic()
        time_since_update = now - self._updated_at
        if time_since_update > 1 * 60:
            self._tokens = self._limit
            self._updated_at = now


class WunderGroundError(Exception):
    status = 422
    description = 'an error has occured while processing'
    type_ = 'api error'

    def __init__(self, type_=None, description=None, status=None):
        if description is not None:
            self.description = description
        if status is not None:
            self.status = status
        if type_ is not None:
            self.type_ = type_
        super().__init__('%s: %s' % (self.status, self.description))


class ParameterError(WunderGroundError):
    status = 406
    description = 'incorrect location parameters passed for query'


class Client(object):
    def __init__(
            self,
            session,
            key,
            url='http://api.wunderground.com/api',
            limit=10):
        '''
        WunderGround API client

        @param session    - aiohttp.ClientSession
        @param key -      - WunderGround API key
        @param url        - base WunderGround API URL
                            (defaults to: 'http://api.wunderground.com/api')
        @param limit      - limit of api calls per minute
                            (defaults to: 10 (free tier))
        '''
        self._url = yarl.URL(url)
        self._key = key
        self._session_limiter = TokenBucket(session, limit=limit)

    async def _req(self, method, page, params=None):
        '''
        Issue a request to the given page relative to WunderGround REST URL.

        @param method   - http method
        @param page     - page relative to WunderGround REST URL.
        @param params   - params to send in query string, if any
        @return         - dictionary of response body. JSON responses will be
                          automatically handled.
        @raises         - WunderGroundError if:
                            - status != 200(most likely not json)
                            - 'error' in rjson['response']

        Note: From studiyng their API, I have noticed only get requests, with
        query strings in some cases. No data to be sent in the request body.
        That can be added when wunderground allows posting data to their API.
        '''
        url = self._url.with_path('%s/%s/%s' % (
            self._url.path.rstrip('/'), self._key, page.lstrip('/')))
        if params is None:
            params = {}

        r = await self._session_limiter.api_call(
                method.lower(),
                url,
                params=params)
        if r.status != 200:
            raise WunderGroundError(
                description=r.reason,
                status=r.status)
        rjson = await r.json()
        if 'error' in rjson['response']:
            error = rjson['response']['error']
            raise WunderGroundError(
                type_=error['type'],
                description=error.get('description'))
        return rjson

    async def get(self, feature, query, settings=None):
        '''
        Get a certain feature from wunderground API, with certain settings and
        location in the query.
        More info at:
        https://www.wunderground.com/weather/api/d/docs?d=data/index

        @param feature    - a feature to get ex: forecast
        @param query      - dict with location params
        @param settings   - dict with one or more of the :
                                lang   : lang code
                                pws    : 0 or 1
                                bestfct: 0 or 1
        '''
        page = feature
        if settings is not None:
            settings = '/'.join(
                ':'.join((k, str(v))) for k, v in settings.items()
            )
            page = '%s/%s' % (page, settings)
        # If more of the following params are present, this is the precedence
        if 'latitude' in query and 'longitude' in query:
            querystring = '%s,%s' % (query['latitude'], query['longitude'])
        elif 'zipcode' in query:
            querystring = query['zipcode']
        elif 'airportcode' in query:
            querystring = query['airportcode']
        elif 'city' in query and 'state' in query:
            querystring = '%s/%s' % (query['state'], query['city'])
        elif 'city' in query and 'country' in query:
            querystring = '%s/%s' % (query['country'], query['city'])
        else:
            raise ParameterError()
        page = '%s/q/%s.json' % (page, querystring)
        return await self._req('GET', page=page)
