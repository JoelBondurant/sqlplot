var util = (() => {

async function sha256(msg) {
	if (typeof msg == 'number') {
		msg = msg.toString();
	}
	if (typeof msg == 'string') {
		msg = (new TextEncoder()).encode(msg);
	}
	return await crypto.subtle.digest('SHA-256', msg);
}

async function sha512(msg) {
	if (typeof msg == 'number') {
		msg = msg.toString();
	}
	if (typeof msg == 'string') {
		msg = (new TextEncoder()).encode(msg);
	}
	return await crypto.subtle.digest('SHA-512', msg);
}

function bytesToHex(byteArray) {
	return Array.from(new Uint8Array(byteArray), function(byte) {
		return ('0' + (byte & 0xFF).toString(16)).slice(-2);
	}).join('');
}

return {
	'sha256': sha256,
	'sha512': sha512,
	'bytesToHex': bytesToHex
}

})();
