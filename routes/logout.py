import logging

import aiohttp


async def logout(request):
	resp = aiohttp.web.HTTPFound('/')
	resp.del_cookie('user_session')
	resp.del_cookie('query_session')
	return resp

