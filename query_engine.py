#!/usr/bin/env python3

import asyncio
import csv
import logging
import os
import sys

import aiocsv
import aiofiles
import aiofiles.os
import aiohttp
import aioredis
import asyncpg
import orjson


app = {}


async def process_event(event):
	if event['event_type'] == 'new':
		xid = event['xid']
		query_info_sql = 'select * from query where xid = $1'
		async with (app['pg_pool']).acquire(timeout=2) as pgconn:
			query_info = dict(await pgconn.fetchrow(query_info_sql, xid))
		logging.debug(f'query_info: {query_info}')
		connection_xid = query_info['connection_xid']
		query_text = query_info['query_text']
		file_ext = query_text.lower().split('.')[-1]
		fn_hidden = f'/data/distillery/query/.{xid}.{file_ext}'
		fn = f'/data/distillery/query/{xid}.{file_ext}'
		if connection_xid == 'HTTP':
			async with aiohttp.ClientSession() as session:
				async with session.get(query_text) as resp:
					data = await resp.content.read()
			async with aiofiles.open(fn_hidden, 'w') as fh:
				await fh.write(data.decode())
			if os.path.exists(fn):
				await aiofiles.os.remove(fn)
			await aiofiles.os.rename(fn_hidden, fn)
			logging.info(f'Ready: {fn}')
	if event['event_type'] == 'user':
		event = event['event']
		logging.info(event)
		user_xid = event['query_session']['xid']
		query_text = event['query_text']
		connection_xid = event['connection_xid']
		connection_info_sql = 'select * from connection where xid = $1'
		async with (app['pg_pool']).acquire(timeout=2) as pgconn:
			logging.debug(f'{connection_info_sql} {connection_xid}')
			try:
				connection_info = (await pgconn.fetchrow(connection_info_sql, connection_xid))
				logging.debug(connection_info)
				connection_info = dict(connection_info)
			except Exception as ex:
				return
		connection_config = orjson.loads(connection_info['configuration'])
		if connection_info['type'] == 'PostgreSQL':
			try:
				pg = await asyncpg.connect(
					user=connection_config['user'],
					password=connection_config['password'],
					database=connection_config['database'],
					host=connection_config['host'],
					command_timeout=10)
				rs = await pg.fetch(query_text, timeout=20)
			except Exception as ex:
				return
			columns = [*rs[0].keys()]
			data = [[*x.values()] for x in rs]
			logging.debug(f'Query data: {columns}\n{data}')
			fn_hidden = f'/data/distillery/query/.{user_xid}.csv'
			fn = f'/data/distillery/query/{user_xid}.csv'
			async with aiofiles.open(fn_hidden, mode='w', newline='') as fout:
				writer = aiocsv.AsyncWriter(fout, dialect='unix')
				await writer.writerow(columns)
				await writer.writerows(data)
			if os.path.exists(fn):
				await aiofiles.os.remove(fn)
			await aiofiles.os.rename(fn_hidden, fn)
			logging.info(f'Ready: {fn}')
			await app['redis'].publish_json(user_xid, {'status':'ready'})


async def channel_reader(channel):
	async for msg in channel.iter():
		event = orjson.loads(msg.decode())
		logging.debug(f'Query Event: {event}')
		await process_event(event)


async def main():
	logging.basicConfig(level=logging.DEBUG)
	logging.info('Starting query engine')
	logging.info(f'Python version: {sys.version}')
	async with aiofiles.open('/secrets/distillery.json', 'r') as fin:
		config = orjson.loads(await fin.read())
	app['config'] = config
	pg_config = config['postgres']
	pg_pool = await asyncpg.create_pool(
		user=pg_config['user'],
		password=pg_config['password'],
		database=pg_config['database'],
		host=pg_config['host'],
		command_timeout=10)
	app['pg_pool'] = pg_pool
	redis_config = config['redis']
	redis = await aioredis.create_redis_pool(
		'redis://'+redis_config["host"],
		password=redis_config['password'])
	app['redis'] = redis
	channel = (await redis.subscribe('query'))[0]
	asyncio.get_running_loop().create_task(channel_reader(channel))
	logging.info('Listening for queries...')
	while True:
		await asyncio.sleep(2)
	logging.info('Stopping query engine.')


if __name__ == '__main__':
	asyncio.run(main())

