import logging

import aioboto3
import aiohttp.web

from routes import login
from routes import authorization


async def data(request):
	user_session, user_xid = login.authenticate(request)
	redis = request.app['redis']
	rquery = dict(request.query)
	if 'xid' in rquery:
		xid = rquery['xid']
	if xid[:3] == 'x20':
		async with (request.app['pg_pool']).acquire(timeout=2) as pgconn:
			assert (await pgconn.fetchval('''
				select count(1)
				from "query" q
				join "authorization" a
					on (q.xid = a.object_xid and a.object_type = 'query')
				join "team_membership" tm
					on (a.type in ('creator','editor', 'reader') and a.team_xid = tm.team_xid)
				where q.xid = $1 and tm.user_xid = $2
			''', xid, user_xid)) > 0
		query_url_key = f'{xid}.query_url'
		query_url = await redis.get(query_url_key)
		if query_url is None:
			aws = aioboto3.Session()
			async with aws.client('s3') as s3:
				query_url = await s3.generate_presigned_url('get_object',
					Params={'Bucket':'sqlplot', 'Key':f'query/{xid}.csv'},
					ExpiresIn=3600*24)
			await redis.set(query_url_key, query_url, expire=3600*24)
		else:
			query_url = query_url.decode()
		return aiohttp.web.json_response({'url': query_url})
