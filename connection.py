import logging
import secrets

import aiohttp
import aiohttp_jinja2
import ujson


TYPES = {
	'PostgreSQL',
	'MySQL',
}

FORM_FIELDS = [
	'name',
	'type',
	'configuration',
]


def is_valid(form):
	if form['type'] not in TYPES:
		return False
	return True


@aiohttp_jinja2.template('html/connection.html')
async def connection(request):
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xconnection_id'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			form = await request.post()
			if is_valid(form):
				record = tuple([secrets.token_hex(16)] + [form[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('connection', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/connection')
		connections = await pgconn.fetch(f'select {", ".join(columns)} from connection', timeout=4)
		connections = [dict(x) for x in connections]
		for x in connections:
			x['configuration'] = ujson.loads(x['configuration'])
			if 'password' in x['configuration']:
				x['configuration']['password'] = '*****'
		return {'connections': connections}

