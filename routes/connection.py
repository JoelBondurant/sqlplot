import logging
import secrets

import aiohttp
import aiohttp_jinja2
from cryptography.fernet import Fernet
import orjson

from routes import login
from routes import authorization


TYPES = {
	'PostgreSQL',
	'MySQL',
}


FORM_FIELDS = [
	'name',
	'type',
	'configuration',
]


FERNET_KEY = None


async def connection(request):
	global FERNET_KEY
	if not FERNET_KEY:
		FERNET_KEY = Fernet(request.app['config']['connection']['key'])
	user_session, user_xid = login.authenticate(request)
	columns = ['xid'] + FORM_FIELDS.copy()
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'Connection event posted: {event}')
			if event['event_type'] == 'new':
				event['configuration'] = FERNET_KEY.encrypt(event['configuration'].encode()).decode()
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid] + [event[k] for k in FORM_FIELDS])
				result = await pgconn.copy_records_to_table('connection', records=[record], columns=columns)
				editors = [('editor', txid, 'connection', xid) for txid in event['editors']]
				readers = [('reader', txid, 'connection', xid) for txid in event['readers']]
				auth = editors + readers + [('creator', user_xid[:-4]+'0000', 'connection', xid)]
				await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'update':
				event['configuration'] = FERNET_KEY.encrypt(event['configuration'].encode()).decode()
				xid = event['xid']
				await pgconn.execute('''
					update "connection" c
					set name = $3, configuration = $4, updated = timezone('utc', now())
					from "authorization" a
					join "team_membership" tm
						on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					where c.xid = $1 and tm.user_xid = $2
						and (c.xid = a.object_xid and a.object_type = 'connection');
				''', xid, user_xid, event['name'], event['configuration'])
				await pgconn.execute('''
					delete from "authorization"
					where "type" in ('editor','reader')
						and object_type = 'connection'
						and object_xid = $1;
				''', xid)
				editors = [('editor', txid, 'connection', xid) for txid in event['editors']]
				readers = [('reader', txid, 'connection', xid) for txid in event['readers']]
				auth = editors + readers
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'delete':
				xid = event['xid']
				await pgconn.execute('''
					delete from "connection" c
					using "authorization" a, "team_membership" tm
					where (c.xid = a.object_xid and a.object_type = 'connection')
					and (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					and c.xid = $1 and tm.user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		# GET:
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			conn = dict(await pgconn.fetchrow(f'''
				select distinct {", ".join(['c.' + c for c in columns])}
				from "connection" c
				left join "authorization" a
					on (c.xid = a.object_xid and a.object_type = 'connection')
				left join "team_membership" tm
					on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
				where c.xid = $1
				and (tm.user_xid = $2)
				''', xid, user_xid, timeout=4))
			conn['configuration'] = FERNET_KEY.decrypt(conn['configuration'].encode()).decode()
			auth = await pgconn.fetch(f'''
				select type, team_xid
				from "authorization"
				where object_type = 'connection'
				and object_xid = $1;
			''', xid, timeout=4)
			editors = [x[1] for x in auth if x[0] == 'editor']
			readers = [x[1] for x in auth if x[0] == 'reader']
			conn['editors'] = editors
			conn['readers'] = readers
			return aiohttp.web.json_response(conn)
		connections = await pgconn.fetch(f'''
			select distinct c.xid, c.name
			from connection c
			left join "authorization" a
				on (c.xid = a.object_xid and a.object_type = 'connection')
			left join "team_membership" tm
				on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
			where (tm.user_xid = $1)
			order by 2, 1
			''', user_xid, timeout=4)
		connections = [dict(x) for x in connections]
		teams = await pgconn.fetch(f'''
			select distinct t.xid, t.name
			from team_membership tm
			join team t
				on (tm.team_xid = t.xid)
			where tm.user_xid = $1
				and not t.xid = left($1,28)||'0000'
			order by 2, 1
			''', user_xid, timeout=4)
		teams = [dict(x) for x in teams]
		context = {
			'connections': connections,
			'teams': teams
		}
		resp = aiohttp_jinja2.render_template('connection.html', request, context)
		return resp

