import asyncio
import logging

import aiohttp
import jwt
import orjson



async def process_event(event, resp):
	logging.debug(f'Results event handler: {event}')
	await resp.send_json({'status':'ready'})


async def channel_reader(channel, resp):
	async for msg in channel.iter():
		event = orjson.loads(msg.decode())
		await process_event(event, resp)


async def results_socket(request):
	logging.info('Results socket opened.')
	startup = True
	resp = aiohttp.web.WebSocketResponse(autoclose=False)
	await resp.prepare(request)
	async for msg in resp:
		subevent = orjson.loads(msg[1])
		logging.debug(f'Subevent: {subevent}')
		query_secret = request.app['config']['query_secret']
		subevent['query_session'] = jwt.decode(subevent['query_session'], query_secret)
		event = {'event_type': 'user', 'event': subevent}
		logging.debug(f'Event: {event}')
		if startup:
			user_xid = subevent['query_session']['xid']
			redis = request.app['redis']
			channel = (await redis.subscribe(user_xid))[0]
			asyncio.get_running_loop().create_task(channel_reader(channel, resp))
			startup = False
			logging.info('Listening for results...')
	return resp

