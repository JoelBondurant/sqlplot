import aiohttp_jinja2

from routes import login


async def payment(request):
	user_session, user_xid = login.authenticate(request)
	context = {}
	resp = aiohttp_jinja2.render_template('payment.html', request, context)
	return resp

