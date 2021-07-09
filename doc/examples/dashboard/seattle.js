html(`
<center>
<div style="font-size:20;">Seattle Weather</div>
<br/>
<div style="display: grid; grid-template-columns: 1fr;">
	<div></div>
	<div id='steattle_stripe'></div>
	<div id='seattle'></div>
	<div></div>
</div>
</center>
`);
bindView('steattle_stripe', 'x3a682ddbb98e7e5bf71e58a96ed48cf');
bindView('seattle', 'xd316b3543ea5f3661cb72fd6a4f1b1b');
document.title = 'Seattle Weather';
