import logging
import secrets

import aiohttp
import aiohttp_jinja2
import orjson

from routes import login


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


async def connection(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xid','user_xid'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			form = await request.post()
			if is_valid(form):
				if len(form['xid']) == 32:
					xid = form['xid']
					await pgconn.execute('''
						update connection
						set name = $3, configuration = $4
						where xid = $1 and user_xid = $2;
					''', xid, user_xid, form['name'], form['configuration'])
				else:
					xid = 'x' + secrets.token_hex(16)[1:]
					record = tuple([xid, user_xid] + [form[k] for k in FORM_FIELDS])
					result = await pgconn.copy_records_to_table('connection', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/connection')
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			conn_json = dict(await pgconn.fetchrow(f'''
				select {", ".join(columns)} from connection where xid = $1 and user_xid = $2
			''', xid, user_xid, timeout=4))
			return aiohttp.web.json_response(conn_json)
		connections = await pgconn.fetch(f'''
			select {", ".join(columns)} from connection where user_xid = $1
			''', user_xid, timeout=4)
		connections = [dict(x) for x in connections]
		for x in connections:
			if len(x['configuration']) > 0:
				x['configuration'] = orjson.loads(x['configuration'])
				if 'password' in x['configuration']:
					x['configuration']['password'] = '*****'
		context = {
			'connections': connections,
		}
		resp = aiohttp_jinja2.render_template('connection.html', request, context)
		return resp

