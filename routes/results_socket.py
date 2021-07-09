import asyncio
import html
import logging

import aiohttp
import jwt
import orjson

from routes import login


async def process_event(event, resp):
	logging.debug(f'Results event handler: {event}')
	await resp.send_json({'status':'ready'})


async def channel_reader(channel, resp):
	async for msg in channel.iter():
		event = orjson.loads(msg.decode())
		await process_event(event, resp)


async def results_socket(request):
	logging.info('Results socket opened.')
	user_session, user_xid = login.authenticate(request)
	redis = request.app['redis']
	channel = (await redis.subscribe(user_xid))[0]
	resp = aiohttp.web.WebSocketResponse(autoclose=True)
	asyncio.get_running_loop().create_task(channel_reader(channel, resp))
	await resp.prepare(request)
	async for msg in resp:
		event = orjson.loads(msg[1])
		event['user_xid'] = user_xid
		event['event_type'] = 'user'
		logging.debug(f'Event: {event}')
	return resp

