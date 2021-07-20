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
				editors = [('editor', txid, 'view', xid) for txid in event['editors']]
				readers = [('reader', txid, 'view', xid) for txid in event['readers']]
				auth = editors + readers
				await pgconn.execute('''
					delete from "authorization"
					where object_type = 'view' and object_xid = $1;
				''', xid)
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'update':
				xid = event['xid']
				await pgconn.execute('''
					update view
					set name = $3, configuration = $4, updated = timezone('utc', now())
					where xid = $1 and user_xid = $2;
				''', xid, user_xid, event['name'], event['configuration'])
				await pgconn.execute('''
					delete from "authorization"
					where object_type = 'view' and object_xid = $1;
				''', xid)
				editors = [('editor', txid, 'view', xid) for txid in event['editors']]
				readers = [('reader', txid, 'view', xid) for txid in event['readers']]
				auth = editors + readers
				if len(auth) > 0:
					await pgconn.copy_records_to_table('authorization', records=auth, columns=authorization.COLUMNS)
			elif event['event_type'] == 'delete':
				xid = event['xid']
				await pgconn.execute('''
					delete from authorization
					where object_type = 'connection' and object_xid = $1;
				''', xid)
				await pgconn.execute('''
					delete from view where xid = $1 and user_xid = $2;
				''', xid, user_xid)
			return aiohttp.web.json_response({'xid': xid})
		# GET:
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			view = {'xid': xid}
			config = await pgconn.fetchval(f'''
				select configuration from view where xid = $1 and user_xid = $2 order by name
				''', xid, user_xid, timeout=4)
			view['configuration'] = config
			auth = await pgconn.fetch(f'''
				select type, team_xid from "authorization" where object_type = 'connection' and object_xid = $1;
			''', xid, timeout=4)
			editors = [x[1] for x in auth if x[0] == 'editor']
			readers = [x[1] for x in auth if x[0] == 'reader']
			view['editors'] = editors
			view['readers'] = readers
			return aiohttp.web.json_response(view)
		views = await pgconn.fetch(f'''
			select xid, name from view where user_xid = $1 order by name
			''', user_xid, timeout=4)
		views = [dict(x) for x in views]
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
			'views': views,
			'teams': teams,
		}
		resp = aiohttp_jinja2.render_template('view.html', request, context)
		return resp

