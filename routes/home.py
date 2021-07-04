import logging

import aiohttp_jinja2

from routes import login


async def home(request):
	try:
		user_session, user_xid = login.authenticate(request)
		context = {'login': True, 'user_xid': user_xid}
		logging.debug(f'home login: {user_xid}')
	except Exception as ex:
		logging.debug(f'home exception: {ex}')
		context = {'login': False, 'user_xid': ''}
	resp = aiohttp_jinja2.render_template('home.html', request, context)
	return resp
