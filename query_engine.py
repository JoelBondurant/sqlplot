#!/usr/bin/env python3

import asyncio
import logging
import sys

import asyncpg
import aioredis
import ujson

async def channel_reader(channel):
	async for msg in channel.iter():
		msg = ujson.loads(msg.decode())
		logging.debug(f'{msg}')


async def main():
	logging.basicConfig(level=logging.DEBUG)
	logging.info('Starting query engine')
	logging.info(f'Python version: {sys.version}')
	with open('/secrets/distillery.json', 'r') as fin:
		config = ujson.load(fin)
	redis_connstr = f'redis://{config["redis"]["host"]}'
	redis = await aioredis.create_redis_pool(redis_connstr)
	channel = (await redis.subscribe('query'))[0]
	asyncio.get_running_loop().create_task(channel_reader(channel))
	logging.info('Listening for queries...')
	while True:
		await asyncio.sleep(2)
	logging.info('Stopping query engine.')


if __name__ == '__main__':
	asyncio.run(main())

