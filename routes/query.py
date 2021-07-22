import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login
from routes import authorization


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
	columns = ['xid'] + FORM_FIELDS.copy()
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			redis = request.app['redis']
			event = await request.json()
			logging.debug(f'Query event posted: {event}')
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid] + [event[k] for k in FORM_FIELDS])
				logging.debug(f'Record: {record}')
				result = await pgconn.copy_records_to_table('query', records=[record], columns=columns)
				editors = [('editor', txid, 'query', xid) for txid in event['editors']]
				readers = [('reader', txid, 'query', xid) for txid in event['readers']]
				auth = editors + readers + [('creator', user_xid[:-4]+'0000', 'query', xid)]
				await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
				event = {
					'event_type': 'new',
					'xid': xid,
				}
				redis.publish_json('query', event)
			elif event['event_type'] == 'update':
				xid = event['xid']
				await pgconn.execute('''
					update "query" q
					set name = $3, query_text = $4, updated = timezone('utc', now())
					from "authorization" a
					join "team_membership" tm
						on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					where q.xid = $1 and tm.user_xid = $2
						and (q.xid = a.object_xid and a.object_type = 'query')
				''', xid, user_xid, event['name'], event['query_text'])
				await pgconn.execute('''
					delete from "authorization"
					where "type" in ('editor','reader')
						and object_type = 'query'
						and object_xid = $1;
				''', xid)
				editors = [('editor', txid, 'query', xid) for txid in event['editors']]
				readers = [('reader', txid, 'query', xid) for txid in event['readers']]
				auth = editors + readers
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
				event = {
					'event_type': 'update',
					'xid': xid,
				}
				redis.publish_json('query', event)
			elif event['event_type'] == 'delete':
				xid = event['xid']
				await pgconn.execute('''
					delete from "query" q
					using "authorization" a, "team_membership" tm
					where (q.xid = a.object_xid and a.object_type = 'query')
					and (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					and q.xid = $1 and tm.user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		#GET:
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			query = dict(await pgconn.fetchrow(f'''
				select {", ".join(['q.'+c for c in columns])}
				from "query" q
				left join "authorization" a
					on (q.xid = a.object_xid and a.object_type = 'query')
				left join "team_membership" tm
					on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
				where q.xid = $1
				and (tm.user_xid = $2)
			''', xid, user_xid, timeout=4))
			auth = await pgconn.fetch(f'''
				select type, team_xid
				from "authorization"
				where object_type = 'query'
				and not team_xid = left($2,28)||'0000'
				and object_xid = $1;

			''', xid, user_xid, timeout=4)
			editors = [x[1] for x in auth if x[0] == 'editor']
			readers = [x[1] for x in auth if x[0] == 'reader']
			query['editors'] = editors
			query['readers'] = readers
			return aiohttp.web.json_response(query)
		queries = await pgconn.fetch(f'''
			select distinct {", ".join(['q.'+c for c in columns])}
			from query q
			left join "authorization" a
				on (q.xid = a.object_xid and a.object_type = 'query')
			left join "team_membership" tm
				on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
			where (tm.user_xid = $1)
			order by q.name
			''', user_xid, timeout=4)
		queries = [dict(x) for x in queries]
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
			'queries': queries,
			'connections': connections,
			'teams': teams,
			'user_xid': user_xid,
		}
		resp = aiohttp_jinja2.render_template('query.html', request, context)
		return resp

