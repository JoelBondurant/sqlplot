import logging
import secrets

import aiohttp
import aiohttp_jinja2

FORM_FIELDS = [
	'name',
	'configuration',
]


def is_valid(form):
	return True


async def view(request):
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		rquery = dict(request.query)
		if 'xview_id' in rquery:
			xview_id = rquery['xview_id']
			config = await pgconn.fetchval(f'select configuration from view where xview_id = $1', xview_id, timeout=4)
			return aiohttp.web.json_response(config)
		columns = ['xview_id'] + FORM_FIELDS.copy()
		views = await pgconn.fetch(f'select {", ".join(columns)} from view', timeout=4)
		views = [dict(x) for x in views]
		if request.method == 'POST':
			logging.debug(f'View posted.')
			form = await request.post()
			if is_valid(form):
				xview_id = 'x' + secrets.token_hex(16)[1:]
				record = tuple([xview_id] + [form[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('view', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/view')
		context = {'views': views}
		resp = aiohttp_jinja2.render_template('html/view.html', request, context)
		return resp

