import logging
import secrets

import aiohttp
import aiohttp_jinja2
import orjson

from routes import login


FORM_FIELDS = [
	'name',
]


async def team(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		columns = ['xid'] + FORM_FIELDS.copy()
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'Connection event posted: {event}')
			event['configuration'] = fernet.encrypt(event['configuration'].encode()).decode()
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid] + [event[k] for k in FORM_FIELDS])
				result = await pgconn.copy_records_to_table('team', records=[record], columns=columns)
			elif event['event_type'] == 'update':
				await pgconn.execute('''
					update team
					set name = $2, updated = timezone('utc', now())
					where xid = $1;
				''', event['xid'], event['name'])
			elif event['event_type'] == 'delete':
				await pgconn.execute('''
					delete from team
					where xid = $1;
				''', event['xid'])
			return aiohttp.web.json_response({'xid': event['xid']})
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			team_json = dict(await pgconn.fetchrow(f'''
				select {", ".join(columns)} from team where xid = $1 order by name
			''', xid, timeout=4))
			return aiohttp.web.json_response(team_json)
		teams = await pgconn.fetch(f'''
			select xid, name from team order by name, xid
			''', timeout=4)
		teams = [dict(x) for x in teams]
		context = {
			'teams': teams,
		}
		resp = aiohttp_jinja2.render_template('team.html', request, context)
		return resp

