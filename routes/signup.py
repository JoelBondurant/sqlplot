import datetime
import hashlib
import logging
import secrets

import aiohttp
import aiohttp_jinja2


async def signup(request):
	if request.method == 'POST':
		event = await request.json()
		name = event['name']
		password = event['password']
		prow = event['pow']
		try:
			msg = 'assert len(name) >= 4'
			assert len(name) >= 4
			msg = 'assert len(name) <= 16'
			assert len(name) <= 16
			msg = 'assert len(password) >= 16'
			assert len(password) >= 16
			msg = 'assert len(password) <= 64'
			assert len(password) <= 64
			rand, nonce = map(int, prow.split(';'))
			msg = 'assert len(str(rand)) == 12'
			assert len(str(rand)) == 12
			difficulty = 3
			hashval = hashlib.sha512(hashlib.sha512(
				(str(rand + nonce) + name + password).encode()).digest()).hexdigest()[:difficulty+8]
			msg = 'proof of work validation failure.'
			assert hashval[:difficulty] == '0'*difficulty
			async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
				msg = 'user name taken.'
				assert await pgconn.fetchval('select count(1) from "user" where name = $1', name) == 0
				user_xid = 'x' + secrets.token_hex(16)[1:]
				team_xid = user_xid[:-4] + '0000'
				salt = secrets.token_hex(16)
				key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 10**5).hex()[:32]
				await pgconn.copy_records_to_table('user',
					records=[[user_xid, name, key, salt]], columns=['xid', 'name', 'key', 'salt'])
				await pgconn.copy_records_to_table('team',
					records=[[team_xid, 'self']], columns=['xid','name'])
				await pgconn.copy_records_to_table('team_membership',
					records=[[team_xid, user_xid, True]], columns=['team_xid', 'user_xid', 'is_admin'])
			msg = ''
			status = 'success'
		except:
			status = 'fail'
		resp = aiohttp.web.json_response({'status': status, 'msg': msg})
		return resp
	resp = aiohttp_jinja2.render_template('signup.html', request, {})
	return resp

