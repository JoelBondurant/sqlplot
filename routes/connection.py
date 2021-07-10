import logging
import secrets

import aiohttp
import aiohttp_jinja2
from cryptography.fernet import Fernet
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


async def connection(request):
	user_session, user_xid = login.authenticate(request)
	fernet = Fernet(request.app['config']['connection']['key'])
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xid','user_xid'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'Connection event posted: {event}')
			event['configuration'] = fernet.encrypt(event['configuration'].encode()).decode()
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid, user_xid] + [event[k] for k in FORM_FIELDS])
				result = await pgconn.copy_records_to_table('connection', records=[record], columns=columns)
			elif event['event_type'] == 'update':
				await pgconn.execute('''
					update connection
					set name = $3, configuration = $4, updated = timezone('utc', now())
					where xid = $1 and user_xid = $2;
				''', event['xid'], user_xid, event['name'], event['configuration'])
			elif event['event_type'] == 'delete':
				await pgconn.execute('''
					delete from connection
					where xid = $1 and user_xid = $2;
				''', event['xid'], user_xid)
			return aiohttp.web.json_response({'xid': event['xid']})
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			conn_json = dict(await pgconn.fetchrow(f'''
				select {", ".join(columns)} from connection where xid = $1 and user_xid = $2 order by name
			''', xid, user_xid, timeout=4))
			conn_json['configuration'] = fernet.decrypt(conn_json['configuration'].encode()).decode()
			return aiohttp.web.json_response(conn_json)
		connections = await pgconn.fetch(f'''
			select xid, name from connection where user_xid = $1 order by name, xid
			''', user_xid, timeout=4)
		connections = [dict(x) for x in connections]
		teams = await pgconn.fetch(f'''
			select distinct t.xid, t.name
			from team_membership tm
			join team t
				on (tm.team_xid = t.xid)
			where tm.user_xid = $1
			order by 2, 1
			''', user_xid, timeout=4)
		teams = [dict(x) for x in teams]
		context = {
			'connections': connections,
			'teams': teams
		}
		resp = aiohttp_jinja2.render_template('connection.html', request, context)
		return resp

