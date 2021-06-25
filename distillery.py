#!/usr/bin/env python3

import logging
import sys

import aiofiles
from aiohttp import web
import aiohttp_jinja2
import aioredis
import asyncpg
import jinja2
import ujson
import uvloop

import connection
import dashboard
import home
import query
import view
import ws


async def app_factory(argv=[]):
	uvloop.install()
	app = web.Application()
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(asctime)s %(levelname)-8s %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	)
	logging.info('Distillery Started')
	logging.info(f'Python version: {sys.version}')
	aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./templates'))
	app.add_routes([
		web.get('/', home.home),
		web.get('/connection', connection.connection),
		web.post('/connection', connection.connection),
		web.get('/query', query.query),
		web.post('/query', query.query),
		web.get('/view', view.view),
		web.post('/view', view.view),
		web.get('/dashboard', dashboard.dashboard),
		web.post('/dashboard', dashboard.dashboard),
		web.static('/css/', './static/css/', show_index=False),
		web.static('/data', '/data/distillery/query/', show_index=True),
		web.get('/ws', ws.ws),
	])
	async with aiofiles.open('/secrets/distillery.json', 'r') as fin:
		app['config'] = ujson.loads(await fin.read())
	# PostgreSQL Pool:
	pg_config = app['config']['postgres']
	pg_pool = await asyncpg.create_pool(
		user=pg_config['user'],
		password=pg_config['password'],
		database=pg_config['database'],
		host=pg_config['host'],
		command_timeout=10)
	app['pg_pool'] = pg_pool
	# Redis Pool:
	redis_config = app['config']['redis']
	redis = await aioredis.create_redis_pool(
		'redis://'+redis_config['host'],
		password=redis_config['password'])
	app['redis'] = redis
	return app


def main():
	web.run_app(app_factory(), port=8080)


if __name__ == '__main__':
	main()

