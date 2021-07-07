#!/usr/bin/env python3

import logging
import sys

import aiofiles
from aiohttp import web
import aiohttp_jinja2
import aioredis
import asyncpg
import jinja2
import orjson
import uvloop

from routes import connection
from routes import dashboard
from routes import home
from routes import login
from routes import logout
from routes import query
from routes import query_socket
from routes import results_socket
from routes import signup
from routes import team
from routes import view


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
	aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./html'))
	app.add_routes([
		web.get('/', home.home),
		web.get('/login', login.login),
		web.post('/login', login.login),
		web.get('/logout', logout.logout),
		web.get('/signup', signup.signup),
		web.post('/signup', signup.signup),
		web.get('/connection', connection.connection),
		web.post('/connection', connection.connection),
		web.get('/query', query.query),
		web.post('/query', query.query),
		web.get('/view', view.view),
		web.post('/view', view.view),
		web.get('/team', team.team),
		web.post('/team', team.team),
		web.get('/dashboard', dashboard.dashboard),
		web.post('/dashboard', dashboard.dashboard),
		web.static('/css/', './static/css/', show_index=False, append_version=True),
		web.static('/data', '/data/distillery/query/', show_index=False, append_version=True),
		web.static('/img', '/data/distillery/img/', show_index=False, append_version=True),
		web.get('/query_socket', query_socket.query_socket),
		web.get('/results_socket', results_socket.results_socket),
	])
	async with aiofiles.open('/secrets/distillery.json', 'r') as fin:
		app['config'] = orjson.loads(await fin.read())
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

