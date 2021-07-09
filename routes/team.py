import logging
import secrets
import re

import aiohttp
import aiohttp_jinja2
import orjson

from routes import login


def member_list(list_string, extras=[]):
	members = (','.join(list_string.split('\n'))).split(',')
	members = [m.strip() for m in members]
	members = [m for m in members if re.match('x[0-9a-f]{31}', m)]
	return sorted(set(members + extras))


async def team(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			event = await request.json()
			logging.debug(f'Team event posted: {event}')
			if event['event_type'] == 'new':
				xid = 'x' + secrets.token_hex(16)[1:]
				event['xid'] = xid
				record = tuple([xid, event['name']])
				result = await pgconn.copy_records_to_table('team', records=[record], columns=['xid','name'])
				admins = member_list(event['admins'], [user_xid])
				members = member_list(event['members'])
				records = [(xid, m, True) for m in admins]
				records += [(xid, m, False) for m in members]
				columns = ['team_xid', 'user_xid', 'is_admin']
				await pgconn.copy_records_to_table('team_membership', records=records, columns=columns)
			elif event['event_type'] == 'update':
				await pgconn.execute('''
					update team
					set name = $2, updated = timezone('utc', now())
					where xid = $1;
				''', event['xid'], event['name'])
				await pgconn.execute('''
					delete from team_membership
					where team_xid = $1;
				''', event['xid'])
				admins = member_list(event['admins'], [user_xid])
				members = member_list(event['members'])
				records = [(event['xid'], m, True) for m in admins]
				records += [(event['xid'], m, False) for m in members]
				columns = ['team_xid', 'user_xid', 'is_admin']
				await pgconn.copy_records_to_table('team_membership', records=records, columns=columns)
			elif event['event_type'] == 'delete':
				await pgconn.execute('''
					delete from team
					where xid = $1;
				''', event['xid'])
				await pgconn.execute('''
					delete from team_membership
					where team_xid = $1;
				''', event['xid'])
			return aiohttp.web.json_response({'xid': event['xid']})
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			team = dict(await pgconn.fetchrow(f'''
				select
					t.xid,
					t.name,
					array_agg(atm.user_xid) as admins,
					array_agg(tm.user_xid) as members
				from team t
				left join team_membership atm
					on (t.xid = atm.team_xid and atm.is_admin)
				left join team_membership tm
					on (t.xid = tm.team_xid and not tm.is_admin)
				where t.xid = $1
				group by 1, 2
				order by 2, 1
			''', xid, timeout=4))
			return aiohttp.web.json_response(team)
		teams = await pgconn.fetch(f'''
			select xid, name from team order by name, xid
			''', timeout=4)
		teams = [dict(x) for x in teams]
		context = {
			'teams': teams,
			'user_xid': user_xid,
		}
		resp = aiohttp_jinja2.render_template('team.html', request, context)
		return resp

