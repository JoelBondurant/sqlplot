import asyncio
import datetime
import hashlib
import secrets

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
		user_session = jwt.decode(user_session_encoded, user_session_key, algorithms=['HS256'])
		user_xid = user_session['xid']
		return [user_session, user_xid]
	except:
		raise aiohttp.web.HTTPFound('/logout')


def session(request, session_name):
	session_encoded = request.cookies[session_name]
	session_key = request.app['config'][session_name]['key']
	session = jwt.decode(session_encoded, session_key, algorithms=['HS256'])
	return session


async def login(request):
	if request.method == 'POST':
		await asyncio.sleep(0.2)
		event = await request.json()
		try:
			timebomb = event['timebomb']
			jwt.decode(timebomb, request.app['config']['user']['session_key'], algorithms=['HS256'])
		except:
			resp = aiohttp.web.json_response({'status': 'fail'})
			resp.del_cookie('user_session')
			return resp
		name = event['name']
		password = event['password']
		assert len(name) >= 4
		assert len(password) >= 16
		try:
			async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
				user = await pgconn.fetchrow('select xid, key, salt from "user" where name = $1', name)
				if user is None:
					raise Exception('fail')
			key = hashlib.pbkdf2_hmac('sha256', password.encode(), user['salt'].encode(), 10**5).hex()[:32]
			if secrets.compare_digest(key, user['key']):
				exp = datetime.datetime.utcnow() + datetime.timedelta(days=7)
				user_session = jwt.encode({'xid': user['xid'], 'exp': exp},
					request.app['config']['user']['session_key'], algorithm='HS256').decode()
				resp = aiohttp.web.json_response({'status': 'success'})
				resp.set_cookie('user_session', user_session, max_age=3600*16, httponly=True, samesite='Strict')
				return resp
		except:
			pass
		resp = aiohttp.web.json_response({'status': 'fail'})
		resp.del_cookie('user_session')
		return resp
	timebomb = {'exp': (datetime.datetime.utcnow() + datetime.timedelta(seconds=120))}
	timebomb = jwt.encode(timebomb, request.app['config']['user']['session_key'], algorithm='HS256').decode()
	context = {
		'timebomb': timebomb
	}
	resp = aiohttp_jinja2.render_template('login.html', request, context)
	resp.del_cookie('user_session')
	return resp
