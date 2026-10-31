export const questNpcPoint=world=>({x:(world.spawn?.x??world.width/2)-165,y:world.groundY});
// Same shaded voxel layers, facial detail and breathing frames as player characters.
export const NPC_AVATAR=Object.freeze({skin:'medium',face:'smile',hair:'brown-short',top:'archer-ranger',bottom:'ranger-trousers',shoes:'ranger-boots',hat:'explorer-brown'});
export function drawQuestNpc(c,p,camX,camY,k,{renderer=null,avatar=NPC_AVATAR,now=0}={}){
 const x=(p.x-camX)*k,y=(p.y-camY)*k;if(x<-100*k||x>c.canvas.width+100*k)return;
 c.save();
 // Layered soft ground shadow; sprite rendering is owned by the shared avatar renderer.
 c.fillStyle='#263e3020';c.fillRect(x-21*k,y-2*k,42*k,5*k);c.fillStyle='#263e3020';c.fillRect(x-15*k,y-k,30*k,3*k);
 if(renderer&&avatar)renderer.draw(c,avatar,x,y,k,renderer.frameAt('idle_front',now),false);
 c.translate(x,y);c.scale(k,k);
 c.fillStyle='#3d5948';c.beginPath();c.roundRect(-40,7,80,18,5);c.fill();c.strokeStyle='#b7c99d';c.lineWidth=1;c.stroke();c.font='650 9px system-ui';c.textAlign='center';c.fillStyle='#f6efce';c.fillText('숲지기 모리',0,19);c.restore();
}
