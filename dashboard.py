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


async def dashboard(request):
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			logging.debug(f'Dashboard posted.')
			form = await request.post()
			if is_valid(form):
				xid = 'x' + secrets.token_hex(16)[1:]
				record = tuple([xid] + [form[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				columns = ['xid'] + FORM_FIELDS.copy()
				result = await pgconn.copy_records_to_table('dashboard', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/dashboard')
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			config = await pgconn.fetchval(f'select configuration from dashboard where xid = $1', xid, timeout=4)
			return aiohttp.web.json_response(config)
		if 'xidh' in rquery:
			xidh = rquery['xidh']
			context = {'xid': xidh}
			return aiohttp_jinja2.render_template('html/dashboard_view.html', request, context)
		dashboards = await pgconn.fetch(f'select xid, name from dashboard', timeout=4)
		dashboards = [dict(x) for x in dashboards]
		context = {'dashboards': dashboards}
		resp = aiohttp_jinja2.render_template('html/dashboard.html', request, context)
		return resp
