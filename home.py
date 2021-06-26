import logging

import aiohttp_jinja2


async def home(request):
	logging.debug(f'home hit.')
	context = {}
	resp = aiohttp_jinja2.render_template('home.html', request, context)
	return resp
