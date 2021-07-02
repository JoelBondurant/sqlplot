import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login


FORM_FIELDS = [
	'name',
	'connection_xid',
	'query_text',
]

CONNECTION_XIDS = [
	'HTTP',
]


async def query(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xid', 'user_xid'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			redis = request.app['redis']
			event = await request.json()
			logging.debug(f'Query event posted: {event}')
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				record = tuple([xid, user_xid] + [event[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('query', records=[record], columns=columns)
				event = {
					'event_type': 'new',
					'xid': xid,
				}
				redis.publish_json('query', event)
			elif event['event_type'] == 'update':
				await pgconn.execute('''
					update query
					set name = $3, query_text = $4, updated = timezone('utc', now())
					where xid = $1 and user_xid = $2;
				''', event['xid'], user_xid, event['name'], event['query_text'])
				event = {
					'event_type': 'update',
					'xid': event['xid'],
				}
				redis.publish_json('query', event)
			elif event['event_type'] == 'delete':
				await pgconn.execute('''
					delete from query where xid = $1 and user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			query_json = dict(await pgconn.fetchrow(f'''
				select {", ".join(columns)} from query where xid = $1 and user_xid = $2
			''', xid, user_xid, timeout=4))
			return aiohttp.web.json_response(query_json)
		queries = await pgconn.fetch(f'select {", ".join(columns)} from query', timeout=4)
		queries = [dict(x) for x in queries]
		connection_data = await pgconn.fetch(f'''
			select xid, name from connection where user_xid = $1
			''', user_xid, timeout=4)
		connection_xids = [x[0] for x in connection_data] + CONNECTION_XIDS.copy()
		connection_names = [x[1] for x in connection_data] + CONNECTION_XIDS.copy()
		connection_labels = [*zip(connection_xids, connection_names)]
		query_session = request.cookies['query_session']
		context = {
			'query_session': query_session,
			'queries': queries,
			'connection_labels': connection_labels,
			'user_xid': user_xid,
		}
		resp = aiohttp_jinja2.render_template('query.html', request, context)
		return resp

