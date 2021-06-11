import logging
import secrets

import aiohttp
import aiohttp_jinja2



def is_valid(form):
	if form['type'] not in TYPES:
		return False
	return True


def set_form_defaults(form):
	logging.debug(f'Raw Form: {form}')
	form = {k: form[k] for k in FORM_FIELDS}
	if not form['port'] or form['port'] == '':
		form['port'] = DEFAULT_PORTS[form['type']]
	logging.debug(f'Form: {form}')
	return form


@aiohttp_jinja2.template('html/view.jinja2')
async def view(request):
	return {}

