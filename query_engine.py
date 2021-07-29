#!/usr/bin/env python3

import asyncio
import csv
import logging
import os
import io
import sys

import aioboto3
import aiofiles
import aiohttp
import aioredis
import asyncpg
from cryptography.fernet import Fernet
import orjson


app = {}


async def process_event(event):
	logging.info(event)
	user_xid = event['user_xid']
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
	fernet = Fernet(app['config']['connection']['key'])
	connection_config = fernet.decrypt(connection_info['configuration'].encode()).decode()
	connection_config = orjson.loads(connection_config)
	if connection_info['type'] == 'PostgreSQL':
		try:
			pg = await asyncpg.connect(
				user=connection_config['user'],
				password=connection_config['password'],
				database=connection_config['database'],
				host=connection_config['host'],
				command_timeout=10)
			rs = await pg.fetch(query_text, timeout=20)
			status, msg = 'success', ''
		except Exception as ex:
			rs = []
			status = 'fail'
			msg = type(ex).__name__ + ': ' + ex.message
		aws = aioboto3.Session()
		if event['event_type'] == 'user':
			fn = f'query/{user_xid}.csv'
		else:
			query_xid = event['xid']
			fn = f'query/{query_xid}.csv'
		if len(rs) == 0:
			async with aws.client('s3') as s3:
				await s3.put_object(Body=b'', Bucket='sqlplot', Key=fn)
		else:
			columns = [*rs[0].keys()]
			data = [[*x.values()] for x in rs]
			logging.debug(f'Query data: {columns}\n{data}')
			csvram = io.StringIO()
			csvwriter = csv.writer(csvram, delimiter=',')
			csvwriter.writerows([columns] + data)
			async with aws.client('s3') as s3:
				await s3.put_object(Body=csvram.getvalue().encode(), Bucket='sqlplot', Key=fn)
			logging.info(f'Ready: {fn}')
		if event['event_type'] == 'user':
			await app['redis'].publish_json(user_xid, {'status':status, 'msg':msg})


async def channel_reader(channel):
	async for msg in channel.iter():
		event = orjson.loads(msg.decode())
		logging.debug(f'Query Event: {event}')
		await process_event(event)


async def main():
	logging.basicConfig(level=logging.DEBUG)
	logging.info('Starting query engine')
	logging.info(f'Python version: {sys.version}')
	async with aiofiles.open('/secrets/sqlplot.json', 'r') as fin:
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

