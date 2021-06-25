import asyncio
import logging

import aiohttp


async def ws(request):
	logging.info('websocket hit')
	resp = aiohttp.web.WebSocketResponse()
	await resp.prepare(request)
	async for msg in resp:
		rmsg = f'Server-side websocket message: {msg.data}'
		logging.info(rmsg)
		await asyncio.sleep(10)
		await resp.send_str(rmsg)
		logging.info('Client response sent.')
	return resp

