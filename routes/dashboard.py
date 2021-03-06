import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login
from routes import authorization
from routes import team


FORM_FIELDS = [
	'name',
	'configuration',
]


async def dashboard(request):
	user_session, user_xid = login.authenticate(request)
	columns = ['xid'] + FORM_FIELDS.copy()
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'Dashboard event posted: {event}')
			if event['event_type'] ==  'new':
				xid = 'x40' + secrets.token_hex(15)[1:]
				event['xid'] = xid
				record = tuple([xid] + [event[k] for k in FORM_FIELDS])
				result = await pgconn.copy_records_to_table('dashboard', records=[record], columns=columns)
				editors = [('editor', txid, 'dashboard', xid) for txid in event['editors']]
				readers = [('reader', txid, 'dashboard', xid) for txid in event['readers']]
				auth = editors + readers + [('creator', team.self_xid(user_xid), 'dashboard', xid)]
				await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'update':
				xid = event['xid']
				await pgconn.execute('''
					update "dashboard" d
					set name = $3, configuration = $4, updated = timezone('utc', now())
					from "authorization" a
					join "team_membership" tm
						on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					where d.xid = $1 and tm.user_xid = $2
						and (d.xid = a.object_xid and a.object_type = 'dashboard');
				''', xid, user_xid, event['name'], event['configuration'])
				await pgconn.execute('''
					delete from "authorization"
					where "type" in ('editor','reader')
						and object_type = 'dashboard'
						and object_xid = $1;
				''', xid)
				editors = [('editor', txid, 'dashboard', xid) for txid in event['editors']]
				readers = [('reader', txid, 'dashboard', xid) for txid in event['readers']]
				auth = editors + readers
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'delete':
				xid = event['xid']
				await pgconn.execute('''
					delete from "dashboard" d
					using "authorization" a, "team_membership" tm
					where (d.xid = a.object_xid and a.object_type = 'dashboard')
					and (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
					and d.xid = $1 and tm.user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		# GET:
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			dashboard = dict(await pgconn.fetchrow(f'''
				select distinct {", ".join(['d.' + c for c in columns])}
				from "dashboard" d
				left join "authorization" a
					on (d.xid = a.object_xid and a.object_type = 'dashboard')
				left join "team_membership" tm
					on (a.type in ('creator','editor','reader') and a.team_xid = tm.team_xid)
				where d.xid = $1
					and (tm.user_xid = $2)
			''', xid, user_xid, timeout=4))
			auth = await pgconn.fetch(f'''
				select type, team_xid
				from "authorization"
				where object_type = 'dashboard'
					and "type" in ('editor','reader')
					and object_xid = $1;
			''', xid, timeout=4)
			editors = [x[1] for x in auth if x[0] == 'editor']
			readers = [x[1] for x in auth if x[0] == 'reader']
			dashboard['editors'] = editors
			dashboard['readers'] = readers
			return aiohttp.web.json_response(dashboard)
		if 'xidh' in rquery:
			xidh = rquery['xidh']
			context = {'xid': xidh}
			return aiohttp_jinja2.render_template('dashboard_view.html', request, context)
		dashboards = await pgconn.fetch(f'''
			select distinct d.xid, d.name
			from "dashboard" d
			left join "authorization" a
				on (d.xid = a.object_xid and a.object_type = 'dashboard')
			left join "team_membership" tm
				on (a.type in ('creator','editor') and a.team_xid = tm.team_xid)
			where (tm.user_xid = $1)
			order by 2, 1
		''', user_xid, timeout=4)
		dashboards = [dict(x) for x in dashboards]
		teams = await pgconn.fetch(f'''
			select distinct t.xid, t.name
			from team_membership tm
			join team t
				on (tm.team_xid = t.xid)
			where tm.user_xid = $1
				and not t.xid = 'x02'||right($1,29)
			order by 2, 1
		''', user_xid, timeout=4)
		teams = [dict(x) for x in teams]
		context = {
			'dashboards': dashboards,
			'teams': teams,
		}
		resp = aiohttp_jinja2.render_template('dashboard.html', request, context)
		return resp

