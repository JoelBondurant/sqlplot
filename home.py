import logging

import aiohttp_jinja2


@aiohttp_jinja2.template('html/home.html')
async def home(request):
	logging.debug(f'Home hit.')
	return {}

