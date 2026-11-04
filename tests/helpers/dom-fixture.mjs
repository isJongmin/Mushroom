// A small event/attribute fixture for component logic. This is not browser layout QA.
export function installDomFixture({createCanvas}){
 class Node extends EventTarget{
  constructor(tag='#text',text=''){super();this.tagName=tag.toUpperCase();this.children=[];this.attrs=new Map();this.dataset={};this.style={setProperty(k,v){this[k]=v;}};this._text=text;this.hidden=false;this.disabled=false;this.value='';}
  setAttribute(k,v){this.attrs.set(k,String(v));if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=String(v);if(k==='disabled')this.disabled=true;if(k==='hidden')this.hidden=true;if(k==='value')this.value=String(v);if(k==='width'||k==='height')this[k]=Number(v);}
  removeAttribute(k){this.attrs.delete(k);}
  focus(){}
  insertBefore(node,before){const at=this.children.indexOf(before);if(at<0)return this.appendChild(node);this.children.splice(at,0,node);node.parentNode=this;return node;}
  closest(selector){if(selector.startsWith('.')&&(this.className||'').split(' ').includes(selector.slice(1)))return this;return this.parentNode?.closest(selector)||null;}
  prepend(...nodes){this.children.unshift(...nodes);}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  contains(node){return this===node||this.children.some(n=>n.contains(node));}
  getAttribute(k){return this.attrs.get(k)??null;}
  appendChild(child){this.children.push(child);child.parentNode=this;return child;}
  append(...nodes){for(const n of nodes)this.appendChild(n);}
  get textContent(){return this._text+this.children.map(n=>n.textContent).join('');}
  set textContent(v){this._text=String(v);this.children=[];}
  getContext(kind){this.canvas ||= createCanvas(this.width||300,this.height||150);return this.canvas.getContext(kind);}
 }
 globalThis.Node=Node;
 globalThis.document={createElement:tag=>new Node(tag),createTextNode:text=>new Node('#text',String(text))};
 return {find(root,id){if(root.getAttribute('data-testid')===id)return root;for(const child of root.children){const found=this.find(child,id);if(found)return found;}return null;},all(root){return [root,...root.children.flatMap(n=>this.all(n))];}};
}
