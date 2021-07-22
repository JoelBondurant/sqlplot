import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login
from routes import authorization


FORM_FIELDS = [
	'name',
	'configuration',
]


async def view(request):
	user_session, user_xid = login.authenticate(request)
	columns = ['xid'] + FORM_FIELDS.copy()
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'View event posted: {event}')
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid] + [event[k] for k in FORM_FIELDS])
				result = await pgconn.copy_records_to_table('view', records=[record], columns=columns)
				editors = [('editor', txid, 'view', xid) for txid in event['editors']]
				readers = [('reader', txid, 'view', xid) for txid in event['readers']]
				auth = editors + readers + [('creator', user_xid[:-4]+'0000', 'view', xid)]
				await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'update':
				xid = event['xid']
				await pgconn.execute('''
					update "view" v
					set name = $3, configuration = $4, updated = timezone('utc', now())
					from "authorization" a
					join "team_membership" tm
						on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					where v.xid = $1 and tm.user_xid = $2
						and (v.xid = a.object_xid and a.object_type = 'view');
				''', xid, user_xid, event['name'], event['configuration'])
				await pgconn.execute('''
					delete from "authorization"
					where "type" in ('editor','reader')
						and object_type = 'view'
						and object_xid = $1;
				''', xid)
				editors = [('editor', txid, 'view', xid) for txid in event['editors']]
				readers = [('reader', txid, 'view', xid) for txid in event['readers']]
				auth = editors + readers
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'delete':
				xid = event['xid']
				await pgconn.execute('''
					delete from "view" v
					using "authorization" a, "team_membership" tm
					where (v.xid = a.object_xid and a.object_type = 'view')
					and (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					and v.xid = $1 and tm.user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		# GET:
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			view = dict(await pgconn.fetchrow(f'''
				select distinct {", ".join(['v.' + c for c in columns])}
				from "view" v
				left join "authorization" a
					on (v.xid = a.object_xid and a.object_type = 'view')
				left join "team_membership" tm
					on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
				where v.xid = $1
					and (tm.user_xid = $2)
			''', xid, user_xid, timeout=4))
			auth = await pgconn.fetch(f'''
				select type, team_xid
				from "authorization"
				where object_type = 'view'
					and object_xid = $1;
			''', xid, timeout=4)
			editors = [x[1] for x in auth if x[0] == 'editor']
			readers = [x[1] for x in auth if x[0] == 'reader']
			view['editors'] = editors
			view['readers'] = readers
			return aiohttp.web.json_response(view)
		views = await pgconn.fetch(f'''
			select distinct v.xid, v.name
			from "view" v
			left join "authorization" a
				on (v.xid = a.object_xid and a.object_type = 'view')
			left join "team_membership" tm
				on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
			where (tm.user_xid = $1)
			order by 2, 1
		''', user_xid, timeout=4)
		views = [dict(x) for x in views]
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
			'views': views,
			'teams': teams,
		}
		resp = aiohttp_jinja2.render_template('view.html', request, context)
		return resp

