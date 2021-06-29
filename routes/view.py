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
		if request.method == 'POST':
			form = await request.post()
			if is_valid(form):
				if len(form['xid']) == 32:
					xid = form['xid']
					record = tuple([xid] + [form[k] for k in FORM_FIELDS])
					await pgconn.execute('''
						update view
						set name = $2, configuration = $3
						where xid = $1;
					''', xid, form['name'], form['configuration'])
				else:
					xid = 'x' + secrets.token_hex(16)[1:]
					record = tuple([xid] + [form[k] for k in FORM_FIELDS])
					columns = ['xid'] + FORM_FIELDS.copy()
					result = await pgconn.copy_records_to_table('view', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/view')
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			config = await pgconn.fetchval(f'select configuration from view where xid = $1', xid, timeout=4)
			return aiohttp.web.json_response(config)
		views = await pgconn.fetch(f'select xid, name from view', timeout=4)
		views = [dict(x) for x in views]
		context = {'views': views}
		resp = aiohttp_jinja2.render_template('view.html', request, context)
		return resp

