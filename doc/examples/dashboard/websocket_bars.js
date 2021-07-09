document.title = "Websocket Dashboard";
html(`
<center>
<div id='websocket'></div>
</center>
`);
const data = [
	{"a": "A","b": 28}, {"a": "B","b": 55}, {"a": "C","b": 43},
	{"a": "D","b": 91}, {"a": "E","b": 81}, {"a": "F","b": 53},
	{"a": "G","b": 19}, {"a": "H","b": 87}, {"a": "I","b": 52}
];
bindView('websocket', 'xf02a0e3eadc763d3fe4315d466895d3').then(function(result) {
	const view = result.view;
	const conn = new WebSocket("wss://echo.websocket.org");
	conn.onopen = function(event) {
		conn.onmessage = function(event) {
			view.insert("table", JSON.parse(event.data)).run();}
		const interval = window.setInterval(function() {
			if (data.length) {
				conn.send(JSON.stringify(data.pop()));
			} else {
				clearInterval(interval);
		}}, 1000);}
}).catch(console.warn);
