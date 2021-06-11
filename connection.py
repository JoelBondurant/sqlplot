import logging
import secrets

import aiohttp
import aiohttp_jinja2


TYPES = {
	'PostgreSQL',
	'MySQL',
}

DEFAULT_PORTS = {
	'PostgreSQL': 5432,
	'MySQL': 3306,
}

FORM_FIELDS = [
	'name',
	'type',
	'host',
	'port',
	'database',
	'user',
	'password',
]


def is_valid(form):
	if form['type'] not in TYPES:
		return False
	return True


def set_form_defaults(form):
	logging.debug(f'Raw Form: {form}')
	form = {k: form[k] for k in FORM_FIELDS}
	if not form['port'] or form['port'] == '':
		form['port'] = DEFAULT_PORTS[form['type']]
	logging.debug(f'Form: {form}')
	return form


@aiohttp_jinja2.template('html/connection.jinja2')
async def connection(request):
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xconnection_id'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			form = await request.post()
			form = set_form_defaults(form)
			if is_valid(form):
				record = tuple([secrets.token_hex(16)] + [form[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('connection', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/connection')
		connections = await pgconn.fetch(f'select {", ".join(columns)} from connection', timeout=4)
		return {'connections': connections}

