import asyncio
import logging

import aiohttp
import jwt
import orjson

from routes import login


async def query_socket(request):
	logging.info('Query socket opened.')
	user_session, user_xid = login.authenticate(request)
	redis = request.app['redis']
	resp = aiohttp.web.WebSocketResponse()
	await resp.prepare(request)
	async for msg in resp:
		event = orjson.loads(msg[1])
		event['user_xid'] = user_xid
		event['event_type'] = 'user'
		logging.debug(f'Query socket event: {event}')
		await redis.publish_json('query', event)
	return resp

