import asyncio
import logging

import aiohttp
import ujson


async def ws(request):
	logging.info('websocket hit')
	redis = request.app['redis']
	resp = aiohttp.web.WebSocketResponse()
	await resp.prepare(request)
	async for msg in resp:
		logging.info(f'Server-side websocket message: {msg.data}')
		subevent = ujson.loads(msg[1])
		event = {'event_type': 'user', 'event': subevent}
		redis.publish_json('query', event)
		logging.info('Query request in queue.')
	return resp

