// Dependency-free WebGL2 instanced voxel renderer. Positions use metres, Y is up.
export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function multiply(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;}
export function perspective(fov,aspect,near,far){const f=1/Math.tan(fov/2),d=1/(near-far);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*d,-1,0,0,2*far*near*d,0]);}
export function lookAt(eye,target){const norm=v=>{const d=Math.hypot(...v)||1;return v.map(x=>x/d);},cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);const z=norm(eye.map((v,i)=>v-target[i])),x=norm(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
export function color(hex){return hex.match(/[a-f\d]{2}/gi).slice(0,3).map(v=>parseInt(v,16)/255);}
export function box(list,x,y,z,sx,sy,sz,hex,yaw=0){list.push(x,y,z,sx,sy,sz,yaw,...color(hex));}
export function localBox(list,origin,x,y,z,sx,sy,sz,hex,angle=0){const a=origin.yaw||0,c=Math.cos(a),s=Math.sin(a);box(list,origin.x+x*c+z*s,origin.y+y,origin.z-x*s+z*c,sx,sy,sz,hex,a+angle);}
export function createRenderer(canvas){
 const gl=canvas.getContext('webgl2',{antialias:true,alpha:false,powerPreference:'high-performance'});if(!gl)return createSoftwareRenderer(canvas);
 const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
 const vs=shader(gl.VERTEX_SHADER,`#version 300 es
 precision highp float;layout(location=0)in vec3 vertex;layout(location=1)in vec3 normal;layout(location=2)in vec3 pos;layout(location=3)in vec3 size;layout(location=4)in float yaw;layout(location=5)in vec3 tint;uniform mat4 vp;uniform vec3 eye;out vec3 col;out float dist;
 void main(){float c=cos(yaw),s=sin(yaw);mat3 r=mat3(c,0.,-s,0.,1.,0.,s,0.,c);vec3 p=r*(vertex*size)+pos;vec3 n=r*normal;float sun=max(dot(n,normalize(vec3(-.5,1.,.35))),0.);float shade=.46+sun*.48+max(n.y,0.)*.12;col=tint*shade;dist=length(p-eye);gl_Position=vp*vec4(p,1.);}`);
 const fs=shader(gl.FRAGMENT_SHADER,`#version 300 es
 precision highp float;in vec3 col;in float dist;uniform vec3 sky;out vec4 outColor;void main(){float fog=smoothstep(28.,70.,dist);outColor=vec4(mix(col,sky,fog),1.);}`);
 const program=gl.createProgram();gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.deleteShader(vs);gl.deleteShader(fs);gl.useProgram(program);
 const vertices=[];for(const [n,u,v]of [[[1,0,0],[0,0,-1],[0,1,0]],[[-1,0,0],[0,0,1],[0,1,0]],[[0,1,0],[1,0,0],[0,0,-1]],[[0,-1,0],[1,0,0],[0,0,1]],[[0,0,1],[1,0,0],[0,1,0]],[[0,0,-1],[-1,0,0],[0,1,0]]])for(const [a,b]of [[-1,-1],[1,-1],[1,1],[-1,-1],[1,1],[-1,1]])vertices.push(...n.map((q,i)=>(q+u[i]*a+v[i]*b)*.5),...n);
 const vao=gl.createVertexArray();gl.bindVertexArray(vao);const geometry=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,geometry);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);for(let a=0;a<2;a++){gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,3,gl.FLOAT,false,24,a*12);}
 const instances=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,instances);for(const [a,size,offset]of [[2,3,0],[3,3,12],[4,1,24],[5,3,28]]){gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,size,gl.FLOAT,false,40,offset);gl.vertexAttribDivisor(a,1);}
 gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);const uniforms=Object.fromEntries(['vp','eye','sky'].map(n=>[n,gl.getUniformLocation(program,n)]));let capacity=0,disposed=false;
 return {draw(data,camera,sky='#b6d7cf'){
  if(disposed||gl.isContextLost())return;const ratio=Math.min(devicePixelRatio||1,1.65),w=Math.round(canvas.clientWidth*ratio),h=Math.round(canvas.clientHeight*ratio);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);const bg=color(sky);gl.clearColor(...bg,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(program);gl.bindVertexArray(vao);gl.uniformMatrix4fv(uniforms.vp,false,multiply(perspective(Math.PI/3,w/h,.1,95),lookAt(camera.eye,camera.target)));gl.uniform3fv(uniforms.eye,camera.eye);gl.uniform3fv(uniforms.sky,bg);gl.bindBuffer(gl.ARRAY_BUFFER,instances);const floats=new Float32Array(data);if(floats.byteLength>capacity){capacity=Math.ceil(floats.byteLength/65536)*65536;gl.bufferData(gl.ARRAY_BUFFER,capacity,gl.DYNAMIC_DRAW);}gl.bufferSubData(gl.ARRAY_BUFFER,0,floats);gl.drawArraysInstanced(gl.TRIANGLES,0,36,data.length/10);
 },destroy(){disposed=true;gl.deleteBuffer(geometry);gl.deleteBuffer(instances);gl.deleteVertexArray(vao);gl.deleteProgram(program);}};
}

// Perspective fallback for browsers where GPU contexts are unavailable (including managed previews).
// It renders the same meshes, camera and world, rather than switching to a 2D game.
function createSoftwareRenderer(canvas){
 const ctx=canvas.getContext('2d',{alpha:false});if(!ctx)throw Error('이 브라우저에서 그래픽 화면을 열 수 없습니다.');
 const faces=[[[1,0,0],[0,0,-1],[0,1,0]],[[-1,0,0],[0,0,1],[0,1,0]],[[0,1,0],[1,0,0],[0,0,-1]],[[0,0,1],[1,0,0],[0,1,0]],[[0,0,-1],[-1,0,0],[0,1,0]]],palette=new Map();let disposed=false;
 return {mode:'software',draw(data,camera,sky='#b6d7cf'){
  if(disposed)return;const ratio=Math.min(devicePixelRatio||1,1.25),w=Math.round(canvas.clientWidth*ratio),h=Math.round(canvas.clientHeight*ratio);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
  ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);const matrix=lookAt(camera.eye,camera.target),f=h/(2*Math.tan(Math.PI/6)),polys=[];
  const view=p=>[matrix[0]*p[0]+matrix[4]*p[1]+matrix[8]*p[2]+matrix[12],matrix[1]*p[0]+matrix[5]*p[1]+matrix[9]*p[2]+matrix[13],-(matrix[2]*p[0]+matrix[6]*p[1]+matrix[10]*p[2]+matrix[14])];
  for(let i=0;i<data.length;i+=10){const [x,y,z,sx,sy,sz,a,r,g,b]=data.slice(i,i+10),centre=view([x,y,z]);if(centre[2]<-Math.max(sx,sy,sz)||centre[2]>75)continue;const radius=Math.max(sx,sy,sz)*1.8;if(Math.abs(centre[0])>centre[2]*w/h*.65+radius||Math.abs(centre[1])>centre[2]*.65+radius)continue;const ca=Math.cos(a),sa=Math.sin(a),rot=p=>[p[0]*ca+p[2]*sa,p[1],-p[0]*sa+p[2]*ca];
   for(let face=0;face<faces.length;face++){if(sy===2.3&&y<=-1.15&&face!==2)continue;const [normal,u,v]=faces[face],n=rot(normal);if(n[0]*(camera.eye[0]-x)+n[1]*(camera.eye[1]-y)+n[2]*(camera.eye[2]-z)<=0)continue;
    let polygon=[];for(const [j,k]of [[-1,-1],[1,-1],[1,1],[-1,1]]){const q=rot(normal.map((value,axis)=>(value+u[axis]*j+v[axis]*k)*[sx,sy,sz][axis]*.5));polygon.push(view([x+q[0],y+q[1],z+q[2]]));}
    const clipped=[];for(let j=0;j<polygon.length;j++){const a=polygon[j],b=polygon[(j+1)%polygon.length],ain=a[2]>=.12,bin=b[2]>=.12;if(ain)clipped.push(a);if(ain!==bin){const t=(.12-a[2])/(b[2]-a[2]);clipped.push(a.map((v,k)=>v+(b[k]-v)*t));}}
    if(clipped.length<3)continue;const points=clipped.map(p=>[w/2+p[0]*f/p[2],h/2-p[1]*f/p[2]]),depth=clipped.reduce((sum,p)=>sum+p[2],0)/clipped.length;
    const shade=.46+Math.max((n[0]*-.5+n[1]+n[2]*.35)/1.17,0)*.48+Math.max(n[1],0)*.12,key=[r,g,b,Math.round(shade*24)].join(',');let fill=palette.get(key);if(!fill){fill='rgb('+[r,g,b].map(c=>Math.round(Math.min(1,c*shade)*255)).join(',')+')';palette.set(key,fill);}polys.push({points,depth,fill,terrain:sy===2.3});
   }
  }
  polys.sort((a,b)=>Number(b.terrain)-Number(a.terrain)||b.depth-a.depth);for(const {points,fill}of polys){ctx.fillStyle=fill;ctx.beginPath();for(let j=0;j<points.length;j++)ctx[j?'lineTo':'moveTo'](...points[j]);ctx.closePath();ctx.fill();}
 },destroy(){disposed=true;palette.clear();}};
}
