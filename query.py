import logging
import secrets

import aiohttp
import aiohttp_jinja2


FORM_FIELDS = [
	'xconnection_id',
	'query_text',
]

XCONNECTION_IDS = [
	'HTTP',
]

def is_valid(form):
	return True


def set_form_defaults(form):
	logging.debug(f'Raw Form: {form}')
	form = {k: form[k] for k in FORM_FIELDS}
	logging.debug(f'Form: {form}')
	return form


@aiohttp_jinja2.template('html/query.jinja2')
async def query(request):
	logging.debug(f'Starting query response.')
	redis = request.app['redis']
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		logging.debug(f'Database connections acquired.')
		columns = ['xquery_id'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			logging.debug(f'Query posted.')
			form = await request.post()
			form = set_form_defaults(form)
			if is_valid(form):
				xquery_id = secrets.token_hex(16)
				record = tuple([xquery_id] + [form[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('query', records=[record], columns=columns)
				event = {
					'event_type': 'new',
					'xquery_id': xquery_id,
				}
				redis.publish_json('query', event)
				raise aiohttp.web.HTTPFound('/query')
		logging.debug(f'Fetching queries...')
		queries = await pgconn.fetch(f'select {", ".join(columns)} from query', timeout=4)
		logging.debug(f'Fetching connections...')
		cdata = await pgconn.fetch(f'select xconnection_id, name from connection', timeout=4)
		logging.debug(f'Finishing query response.')
		xconnection_ids = XCONNECTION_IDS.copy() + [x[0] for x in cdata]
		xconnection_names = XCONNECTION_IDS.copy() + [x[1] + '-' + x[0] for x in cdata]
		xconnection_labels = [*zip(xconnection_ids, xconnection_names)]
		return {
			'queries': queries,
			'xconnection_labels': xconnection_labels,
		}

