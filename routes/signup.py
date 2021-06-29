import datetime
import hashlib
import logging
import secrets

import aiohttp
import aiohttp_jinja2


async def signup(request):
	if request.method == 'POST':
		form = await request.json()
		name = form['name']
		password = form['password']
		assert len(name) >= 4
		assert len(password) >= 16
		async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
			assert await pgconn.fetchval('select count(1) from "user" where name = $1', name) == 0
			xid = 'x' + secrets.token_hex(16)[1:]
			salt = secrets.token_hex(16)
			key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 10**5).hex()[:32]
			record = [xid, name, key, salt]
			columns = ['xid', 'name', 'key', 'salt']
			result = await pgconn.copy_records_to_table('user', records=[record], columns=columns)
		resp = aiohttp.web.HTTPFound('/login')  # this redirect is done client side, not here.
		return resp
	resp = aiohttp_jinja2.render_template('signup.html', request, {})
	return resp

