import logging

import aiohttp_jinja2


@aiohttp_jinja2.template('html/dashboard.html')
async def dashboard(request):
	logging.debug(f'Dashboard hit.')
	return {}

