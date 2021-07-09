html(`
<center>
<span style='font-size: 40; color: gold;'>Pacman & </span>
<span style='font-size: 40; color: steelblue;'>Dolphin </span><br/>
<hr/><br/><br/>
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr;">
	<div></div>
	<div id='pacman'></div>
	<div id='dolphin'></div>
	<div></div>
</div>
<br/><br/><hr/>
<span style='font-size: 40; color: gold;'>Pacman & </span>
<span style='font-size: 40; color: steelblue;'>Dolphin </span><br/>
</center>
`);
bindView('pacman', 'xdca921dffab4aa28c8095f12d765baf');
bindView('dolphin', 'x14fa387bd7e87c6e53fb6ccb78e78e3');
dashboard().style.backgroundImage = "url('/img/ocean.jpg')";
dashboard().style.backgroundSize = "cover";
dashboard().style.backgroundRepeat = "no-repeat";
document.title = 'Pacman & Dolphin';
