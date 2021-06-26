import datetime
import hashlib
import logging

import aiohttp
import aiohttp_jinja2
import jwt


async def login(request):
	if request.method == 'POST':
		form = await request.json()
		name = form['name']
		password = form['password']
		assert len(name) >= 4
		assert len(password) >= 16
		async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
			user = dict(await pgconn.fetchrow('select xid, key, salt from "user" where name = $1', name))
		key = hashlib.pbkdf2_hmac('sha256', password.encode(), user['salt'].encode(), 10**5).hex()[:32]
		if key == user['key']:
			exp = datetime.datetime.utcnow() + datetime.timedelta(days=7)
			token = jwt.encode({'xid': user['xid'], 'exp': exp}, request.app['config']['user_secret'])
		else:
			token = 'fail'
		resp = aiohttp.web.HTTPFound('/')  # redirect done client side, not here.
		resp.set_cookie('session', token, max_age=3600*24*7, httponly=True, samesite='Strict')
		return resp
	resp = aiohttp_jinja2.render_template('login.html', request, {})
	return resp

