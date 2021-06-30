import logging
import secrets

import aiohttp
import aiohttp_jinja2

from routes import login


FORM_FIELDS = [
	'name',
	'configuration',
]


def is_valid(form):
	return True


async def view(request):
	user_session, user_xid = login.authenticate(request)
	async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
		if request.method == 'POST':
			form = await request.post()
			if is_valid(form):
				if len(form['xid']) == 32:
					await pgconn.execute('''
						update view
						set name = $3, configuration = $4, updated = timezone('utc', now())
						where xid = $1 and user_xid = $2;
					''', form['xid'], user_xid, form['name'], form['configuration'])
				else:
					xid = 'x' + secrets.token_hex(16)[1:]
					record = tuple([xid, user_xid] + [form[k] for k in FORM_FIELDS])
					columns = ['xid', 'user_xid'] + FORM_FIELDS.copy()
					result = await pgconn.copy_records_to_table('view', records=[record], columns=columns)
				raise aiohttp.web.HTTPFound('/view')
		rquery = dict(request.query)
		if 'xid' in rquery:
			xid = rquery['xid']
			config = await pgconn.fetchval(f'''
				select configuration from view where xid = $1 and user_xid = $2
				''', xid, user_xid, timeout=4)
			return aiohttp.web.json_response(config)
		views = await pgconn.fetch(f'select xid, name from view where user_xid = $1', user_xid, timeout=4)
		views = [dict(x) for x in views]
		context = {'views': views}
		resp = aiohttp_jinja2.render_template('view.html', request, context)
		return resp

