#!/usr/bin/env python3

import asyncio
import logging
import os
import sys

import aiofiles
import aiofiles.os
import aiohttp
import aioredis
import asyncpg
import ujson


app = {}


async def process_event(event):
	if event['event_type'] == 'new':
		xquery_id = event['xquery_id']
		async with (app['pg_pool']).acquire(timeout=2) as pgconn:
			query_info_sql = 'select * from query where xquery_id = $1'
			query_info = dict(await pgconn.fetchrow(query_info_sql, xquery_id))
			logging.debug(f'query_info: {query_info}')
			xconnection_id = query_info['xconnection_id']
			query_text = query_info['query_text']
			file_ext = query_text.lower().split('.')[-1]
			fn_hidden = f'/data/distillery/query/.{xquery_id}.{file_ext}'
			fn = f'/data/distillery/query/{xquery_id}.{file_ext}'
			if xconnection_id == 'HTTP':
				async with aiohttp.ClientSession() as session:
					async with session.get(query_text) as resp:
						data = await resp.content.read()
				async with aiofiles.open(fn_hidden, 'w') as fh:
					await fh.write(data.decode())
				if os.path.exists(fn):
					await aiofiles.os.remove(fn)
				await aiofiles.os.rename(fn_hidden, fn)
				logging.info(f'Ready: {fn}')


async def channel_reader(channel):
	async for msg in channel.iter():
		event = ujson.loads(msg.decode())
		logging.debug(f'Query Event: {event}')
		await process_event(event)


async def main():
	logging.basicConfig(level=logging.DEBUG)
	logging.info('Starting query engine')
	logging.info(f'Python version: {sys.version}')
	with open('/secrets/distillery.json', 'r') as fin:
		config = ujson.load(fin)
	app['config'] = config
	pg_config = config['postgres']
	pg_pool = await asyncpg.create_pool(
		user=pg_config['user'],
		password=pg_config['password'],
		database=pg_config['database'],
		host=pg_config['host'],
		command_timeout=10)
	app['pg_pool'] = pg_pool
	redis_connstr = f'redis://{config["redis"]["host"]}'
	redis = await aioredis.create_redis_pool(redis_connstr)
	app['redis'] = redis
	channel = (await redis.subscribe('query'))[0]
	asyncio.get_running_loop().create_task(channel_reader(channel))
	logging.info('Listening for queries...')
	while True:
		await asyncio.sleep(2)
	logging.info('Stopping query engine.')


if __name__ == '__main__':
	asyncio.run(main())

