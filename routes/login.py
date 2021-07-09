import asyncio
import datetime
import hashlib
import logging

import aiohttp
import aiohttp_jinja2
import jwt


def authenticate(request):
	try:
		user_session_encoded = request.cookies['user_session']
	except:
		raise aiohttp.web.HTTPFound('/login')
	try:
		user_session_key = request.app['config']['user']['session_key']
		user_session = jwt.decode(user_session_encoded, user_session_key)
		user_xid = user_session['xid']
		return [user_session, user_xid]
	except:
		raise aiohttp.web.HTTPFound('/logout')


def session(request, session_name):
	session_encoded = request.cookies[session_name]
	session_key = request.app['config'][session_name]['key']
	session = jwt.decode(session_encoded, session_key)
	return session


async def login(request):
	if request.method == 'POST':
		await asyncio.sleep(0.2)
		form = await request.json()
		name = form['name']
		password = form['password']
		assert len(name) >= 4
		assert len(password) >= 16
		try:
			async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
				user = await pgconn.fetchrow('select xid, key, salt from "user" where name = $1', name)
				if user is None:
					raise Exception('fail')
			key = hashlib.pbkdf2_hmac('sha256', password.encode(), user['salt'].encode(), 10**5).hex()[:32]
			if key == user['key']:
				exp = datetime.datetime.utcnow() + datetime.timedelta(days=7)
				user_session = jwt.encode({'xid': user['xid'], 'exp': exp},
					request.app['config']['user']['session_key']).decode()
				resp = aiohttp.web.json_response({'status': 'success'})
				resp.set_cookie('user_session', user_session, max_age=3600*24, httponly=True, samesite='Strict')
				return resp
		except:
			pass
		resp = aiohttp.web.json_response({'status': 'fail'})
		resp.del_cookie('user_session')
		return resp
	resp = aiohttp_jinja2.render_template('login.html', request, {})
	resp.del_cookie('user_session')
	return resp

