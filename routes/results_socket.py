import asyncio
import html
import logging

import aioboto3
import aiohttp
import jwt
import orjson

from routes import login


async def process_event(event, resp):
	logging.debug(f'Results event handler: {event}')
	await resp.send_json(event)


async def channel_reader(channel, resp):
	async for msg in channel.iter():
		event = orjson.loads(msg.decode())
		await process_event(event, resp)


async def results_socket(request):
	logging.info('Results socket opened.')
	user_session, user_xid = login.authenticate(request)
	redis = request.app['redis']
	query_url_key = f'{user_xid}.query_url'
	query_url = await redis.get(query_url_key)
	if query_url is None:
		aws = aioboto3.Session()
		async with aws.client('s3') as s3:
			query_url = await s3.generate_presigned_url('get_object',
				Params={'Bucket':'sqlplot', 'Key':f'query/{user_xid}.csv'},
				ExpiresIn=3600*24)
		await redis.put(query_url_key, query_url, ExpiresIn=3600*24)
	channel = (await redis.subscribe(user_xid))[0]
	resp = aiohttp.web.WebSocketResponse(autoclose=True)
	asyncio.get_running_loop().create_task(channel_reader(channel, resp))
	await resp.prepare(request)
	async for msg in resp:
		event = orjson.loads(msg[1])
		event['user_xid'] = user_xid
		event['event_type'] = 'user'
		logging.debug(f'Result socket event: {event}')
	return resp

