export function readPanelCollapsed(storage,key,fallback=false){try{const v=storage?.getItem(key);return v==='1'?true:v==='0'?false:fallback;}catch{return fallback;}}
export function writePanelCollapsed(storage,key,value){try{storage?.setItem(key,value?'1':'0');}catch{/* The control still works with unavailable storage. */}}
