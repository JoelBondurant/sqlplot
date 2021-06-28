import logging
import secrets

import aiohttp
import aiohttp_jinja2
import jwt


FORM_FIELDS = [
	'name',
	'connection_xid',
	'query_text',
]

CONNECTION_XIDS = [
	'HTTP',
]

def is_valid(form):
	return True


async def query(request):
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xid'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			form = await request.post()
			redis = request.app['redis']
			if is_valid(form):
				if len(form['xid']) == 32:
					xid = form['xid']
					record = tuple([xid] + [form[k] for k in FORM_FIELDS])
					await pgconn.execute('''
						update query
						set name = $2, query_text = $3
						where xid = $1;
					''', xid, form['name'], form['query_text'])
					event = {
						'event_type': 'update',
						'xid': xid,
					}
					redis.publish_json('query', event)
				else:
					xid = 'x' + secrets.token_hex(16)[1:]
					record = tuple([xid] + [form[k] for k in FORM_FIELDS])
					logging.debug(f'Record: {record}')
					result = await pgconn.copy_records_to_table('query', records=[record], columns=columns)
					event = {
						'event_type': 'new',
						'xid': xid,
					}
					redis.publish_json('query', event)
				raise aiohttp.web.HTTPFound('/query')
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			query_json = dict(await pgconn.fetchrow(f'''
				select {", ".join(columns)} from query where xid = $1
			''', xid, timeout=4))
			return aiohttp.web.json_response(query_json)
		queries = await pgconn.fetch(f'select {", ".join(columns)} from query', timeout=4)
		queries = [dict(x) for x in queries]
		cdata = await pgconn.fetch(f'select xid, name from connection', timeout=4)
		connection_xids = CONNECTION_XIDS.copy() + [x[0] for x in cdata]
		connection_names = CONNECTION_XIDS.copy() + [x[1] + '-' + x[0][:4] for x in cdata]
		connection_labels = [*zip(connection_xids, connection_names)]
		query_session = request.cookies['query_session']
		query_secret = request.app['config']['query_secret']
		session = jwt.decode(query_session, query_secret)
		context = {
			'query_session': query_session,
			'queries': queries,
			'connection_labels': connection_labels,
			'user_xid': session['xid'],
		}
		resp = aiohttp_jinja2.render_template('query.html', request, context)
		return resp

