#!/usr/bin/env python3

import logging
import sys

from aiohttp import web
import aiohttp_jinja2
import asyncpg
import aioredis
import jinja2
import ujson

import home
import connection
import query
import view
import dashboard


async def app_factory(argv=[]):
	app = web.Application()
	logging.basicConfig(level=logging.DEBUG)
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
		web.get('/dashboard', dashboard.dashboard),
		web.static('/css/', './static/css/', show_index=False),
	])
	with open('/secrets/distillery.json', 'r') as fin:
		app['config'] = ujson.load(fin)
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
	redis_host = app['config']['redis']['host']
	redis_pool = await aioredis.create_redis_pool(f'redis://{redis_host}')
	app['redis'] = redis_pool
	return app


def main():
	web.run_app(app_factory(), port=8080)


if __name__ == '__main__':
	main()

