import logging

import aiohttp_jinja2


@aiohttp_jinja2.template('html/dashboard.jinja2')
async def dashboard(request):
	logging.debug(f'Dashboard hit.')
	return {}

