// Draw markers in the world layer before actors; DOM buttons are transparent hit targets.
export function drawNpcAction(c,x,y,scale=1){
 c.save();c.translate(x,y);c.scale(scale,scale);
 c.fillStyle='#273b4b';c.beginPath();c.roundRect(-14,-14,28,25,5);c.fill();
 c.strokeStyle='#edcf8e';c.lineWidth=1.5;c.stroke();
 c.fillStyle='#edcf8e';c.beginPath();c.moveTo(-3,11);c.lineTo(0,15);c.lineTo(4,11);c.closePath();c.fill();
 c.fillStyle='#ffe9bb';for(const xx of [-6,0,6])c.fillRect(xx-1.5,-3,3,3);
 c.restore();
}
