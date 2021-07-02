import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login


FORM_FIELDS = [
	'name',
	'configuration',
]


async def view(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'View event posted: {event}')
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid, user_xid] + [event[k] for k in FORM_FIELDS])
				columns = ['xid', 'user_xid'] + FORM_FIELDS.copy()
				result = await pgconn.copy_records_to_table('view', records=[record], columns=columns)
			elif event['event_type'] == 'update':
				await pgconn.execute('''
					update view
					set name = $3, configuration = $4, updated = timezone('utc', now())
					where xid = $1 and user_xid = $2;
				''', event['xid'], user_xid, event['name'], event['configuration'])
			elif event['event_type'] == 'delete':
				await pgconn.execute('''
					delete from view where xid = $1 and user_xid = $2;
				''', event['xid'], user_xid)
			return aiohttp.web.json_response({'xid': event['xid']})
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			config = await pgconn.fetchval(f'''
				select configuration from view where xid = $1 and user_xid = $2 order by name
				''', xid, user_xid, timeout=4)
			return aiohttp.web.json_response(config)
		views = await pgconn.fetch(f'''
			select xid, name from view where user_xid = $1 order by name
			''', user_xid, timeout=4)
		views = [dict(x) for x in views]
		context = {'views': views}
		resp = aiohttp_jinja2.render_template('view.html', request, context)
		return resp

