import asyncio
import logging

import aiohttp
import jwt
import ujson


async def query_socket(request):
	logging.info('Query socket opened.')
	redis = request.app['redis']
	resp = aiohttp.web.WebSocketResponse()
	await resp.prepare(request)
	async for msg in resp:
		subevent = ujson.loads(msg[1])
		query_secret = request.app['config']['query_secret']
		subevent['query_session'] = jwt.decode(subevent['query_session'], query_secret)
		event = {'event_type': 'user', 'event': subevent}
		logging.debug(f'Query socket event: {event}')
		await redis.publish_json('query', event)
	return resp

