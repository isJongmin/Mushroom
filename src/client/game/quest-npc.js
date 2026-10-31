export const questNpcPoint=world=>({x:(world.spawn?.x??world.width/2)-165,y:world.groundY});
export function drawQuestNpc(c,p,camX,camY,k){
 const x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-100*k||x>c.canvas.width+100*k)return;
 c.save();c.translate(x,y);c.scale(k,k);
 const cube=(x,y,w,h,face,top,side)=>{c.fillStyle=face;c.fillRect(x,y,w,h);c.fillStyle=top;c.beginPath();c.moveTo(x,y);c.lineTo(x+4,y-3);c.lineTo(x+w+4,y-3);c.lineTo(x+w,y);c.closePath();c.fill();c.fillStyle=side;c.beginPath();c.moveTo(x+w,y);c.lineTo(x+w+4,y-3);c.lineTo(x+w+4,y+h-3);c.lineTo(x+w,y+h);c.closePath();c.fill();};
 c.fillStyle='#273c3433';c.fillRect(-19,-2,38,5);
 cube(-13,-16,10,15,'#655440','#968064','#493d32');cube(4,-16,10,15,'#655440','#968064','#493d32');
 cube(-17,-45,32,31,'#64805b','#9caf78','#3c5b43');cube(-21,-43,7,24,'#c2ab81','#ecd5ab','#9c805e');cube(16,-43,7,24,'#c2ab81','#ecd5ab','#9c805e');
 cube(-19,-75,36,30,'#dfbc91','#f5d9b2','#ad8764');cube(-22,-80,42,9,'#947146','#c39e65','#6d5539');cube(-15,-86,29,6,'#a17c4c','#d1ad74','#79603e');
 c.fillStyle='#334d3b';c.fillRect(-10,-61,3,4);c.fillRect(7,-61,3,4);c.fillStyle='#a07350';c.fillRect(-3,-51,7,2);c.fillStyle='#ddcf9c';c.fillRect(-6,-40,12,8);
 c.font='700 9px system-ui';c.textAlign='center';c.fillStyle='#fff8d9';c.fillRect(-36,7,76,17);c.fillStyle='#426044';c.fillText('숲지기 모리',2,19);c.restore();
}
