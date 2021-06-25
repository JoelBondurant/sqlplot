import datetime
import logging

import aiohttp
import aiohttp_jinja2


async def login(request):
	if request.method == 'POST':
		async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
			form = await request.post()
			resp = aiohttp.web.HTTPFound('/')
			token = 'mysessionid'
			lifespan = 3600*24*7
			resp.set_cookie('session', token, max_age=lifespan, httponly=True, samesite='Strict')
			return resp
	context = {}
	resp = aiohttp_jinja2.render_template('login.html', request, context)
	return resp

