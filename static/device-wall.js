/* ZDesk multi-device wall. Each tile has its own stream and input queue. */
(()=>{
'use strict';
const deviceList=document.getElementById('devices'), dashboard=document.getElementById('dashboard');
const grid=document.createElement('div');grid.id='wallDevices';grid.className='grid wall-grid';
if(!grid||!dashboard)return;
const bar=document.createElement('div');
bar.className='row wall-toolbar';
bar.innerHTML='<strong>Remote screen wall</strong><label>Columns <select id="wallCols"><option value="auto">Auto</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option></select></label><label><input id="wallLive" type="checkbox"> Live previews</label><button class="secondary" id="wallRefresh" type="button">Refresh</button><span id="wallInfo" class="muted" role="status"></span>';
deviceList.before(bar);bar.after(grid);grid.hidden=true;
const css=document.createElement('style');
css.textContent=`
.wall-toolbar{margin:18px 0}.wall-toolbar label{display:flex;align-items:center;gap:8px;margin:0}
#wallDevices.wall-grid{grid-template-columns:repeat(var(--wall-columns,auto-fit),minmax(min(100%,290px),1fr));align-items:start}
#wallDevices.wall-grid .device{padding:12px;min-width:0;overflow:hidden}
.wall-preview{width:100%;aspect-ratio:16/10;object-fit:contain;background:#070e18;border-radius:9px;display:block;touch-action:none;user-select:none;-webkit-user-select:none}
.wall-preview[hidden]{display:none}
.wall-preview:focus-visible{outline:2px solid #48dfbd}
.wall-status{font-size:12px;min-height:18px;color:#9cacc1}
@media(max-width:650px){#wallDevices.wall-grid{grid-template-columns:repeat(var(--wall-columns,auto-fit),minmax(0,1fr))}#wallDevices.wall-grid .device .row{gap:6px}#wallDevices.wall-grid .device button{font-size:12px;padding:7px}}
`;
document.head.append(css);
grid.classList.add('wall-grid');
const cols=bar.querySelector('#wallCols'),toggle=bar.querySelector('#wallLive'),info=bar.querySelector('#wallInfo');
let tiles=new Map(),epoch=0,active=false,observer=null,refreshing=false;
const visible=new Set();
function credentials(){return typeof password==='string'&&password&&typeof dashboardUnlocked!=='undefined'&&dashboardUnlocked}
function setColumns(){const n=cols.value;grid.style.setProperty('--wall-columns',n==='auto'?'auto-fit':n);grid.style.gridTemplateColumns=n==='auto'?'repeat(auto-fit,minmax(min(100%,290px),1fr))':`repeat(${n},minmax(0,1fr))`;}
cols.onchange=()=>{setColumns();try{localStorage.setItem('zdesk-wall-columns',cols.value)}catch(_){}};try{const saved=localStorage.getItem('zdesk-wall-columns');if(['auto','1','2','3','4'].includes(saved))cols.value=saved}catch(_){}setColumns();
function stop(){grid.hidden=true;grid.replaceChildren();epoch++;active=false;visible.clear();if(observer){observer.disconnect();observer=null}for(const tile of tiles.values()){tile.image?.removeAttribute('src');if(tile.url)URL.revokeObjectURL(tile.url);tile.url=null;tile.pending=false;tile.pointer=null}tiles.clear();}
function sendCommand(tile,command){if(!credentials()||!tile.device?.online||!tile.device.control)return;tile.queue.push(command);if(tile.queue.length>24)tile.queue=[{type:'release'}];flush(tile);}
async function flush(tile){if(tile.sending||!tile.queue.length)return;tile.sending=true;try{while(tile.queue.length&&active&&credentials()){const batch=tile.queue.splice(0,24);const r=await fetch('/api/devices/'+encodeURIComponent(tile.device.id)+'/commands',{method:'POST',headers:{Authorization:'Bearer '+password,'Content-Type':'application/json'},body:JSON.stringify({commands:batch})});if(!r.ok){tile.queue=[];break}}}catch(_){tile.queue=[]}finally{tile.sending=false}}
function point(img,e){const r=img.getBoundingClientRect();return{x:Math.max(0,Math.min(1,(e.clientX-r.left)/Math.max(r.width,1))),y:Math.max(0,Math.min(1,(e.clientY-r.top)/Math.max(r.height,1)))}}
function bindInput(tile){const img=tile.image;img.addEventListener('pointerdown',e=>{if(!tile.device.control||!tile.device.online)return;e.preventDefault();img.setPointerCapture(e.pointerId);img.focus();const p=point(img,e);tile.pointer={id:e.pointerId,start:p,last:p,startX:e.clientX,startY:e.clientY,moved:false,down:e.pointerType==='mouse',button:e.button===2?'right':'left'};if(tile.pointer.down)sendCommand(tile,{type:'pointer_down',...p,button:tile.pointer.button})});
img.addEventListener('pointermove',e=>{const p=tile.pointer;if(!p||p.id!==e.pointerId)return;e.preventDefault();const at=point(img,e);if(!p.down&&Math.hypot(e.clientX-p.startX,e.clientY-p.startY)>8){p.down=true;p.moved=true;sendCommand(tile,{type:'pointer_down',...p.start,button:'left'})}if(p.down){sendCommand(tile,{type:'move',...at});p.last=at}});
function finish(e){const p=tile.pointer;if(!p||p.id!==e.pointerId)return;tile.pointer=null;const at=point(img,e);if(p.down){sendCommand(tile,{type:'move',...at});sendCommand(tile,{type:'pointer_up',...at,button:p.button})}else sendCommand(tile,{type:'click',...at,button:'left'});}
img.addEventListener('pointerup',finish);img.addEventListener('pointercancel',()=>{tile.pointer=null;sendCommand(tile,{type:'release'})});img.addEventListener('lostpointercapture',()=>{if(tile.pointer){tile.pointer=null;sendCommand(tile,{type:'release'})}});
img.addEventListener('contextmenu',e=>e.preventDefault());img.addEventListener('wheel',e=>{if(!tile.device.control)return;e.preventDefault();sendCommand(tile,{type:'scroll',amount:e.deltaY>0?-1:1})},{passive:false});
img.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();img.blur();}else if(e.key==='Escape'){sendCommand(tile,{type:'release'})}});}
async function sync(){if(!active||!credentials()||refreshing)return;refreshing=true;try{const r=await fetch('/api/devices',{headers:{Authorization:'Bearer '+password}});if(!r.ok)return;const devices=await r.json();const current=new Set(devices.map(d=>d.id));for(const [id,t] of tiles)if(!current.has(id)){if(t.url)URL.revokeObjectURL(t.url);t.card?.remove();tiles.delete(id)}
for(const d of devices){let tile=tiles.get(d.id);if(!tile){tile={device:d,url:null,pending:false,sending:false,queue:[],image:null};tiles.set(d.id,tile)}tile.device=d;let card=tile.card;if(!card){card=document.createElement('article');card.className='device';const title=document.createElement('h3');title.textContent=d.name;card.append(title);const open=document.createElement('button');open.className='secondary';open.textContent='Open full controls';open.onclick=()=>selectDevice(tile.device);card.append(open);grid.append(card);tile.card=card}card.querySelector('button').disabled=!d.online;if(!tile.image||tile.image.parentElement!==card){const img=document.createElement('img');img.className='wall-preview';img.alt='Live screen of '+d.name;img.tabIndex=0;img.draggable=false;img.hidden=!d.online;const status=document.createElement('div');status.className='wall-status';card.append(img,status);tile.image=img;tile.status=status;bindInput(tile);observer?.observe(img)}tile.image.hidden=!d.online;tile.status.textContent=d.online?(d.control?'Live · tap or swipe to control':'Live · view only'):'Offline';}
info.textContent=devices.filter(d=>d.online).length+' online · '+devices.length+' paired';
}catch(_){info.textContent='Unable to refresh device wall'}finally{refreshing=false}}
async function poll(){if(!active||!credentials()||document.hidden)return;const generation=epoch;for(const tile of tiles.values()){if(!tile.image||tile.pending||!tile.device.online||!visible.has(tile.image))continue;tile.pending=true;(async()=>{try{const r=await fetch('/api/devices/'+encodeURIComponent(tile.device.id)+'/frame',{headers:{Authorization:'Bearer '+password},cache:'no-store'});if(!r.ok)return;const blob=await r.blob();if(generation!==epoch||!tile.image?.isConnected)return;const url=URL.createObjectURL(blob),previous=tile.url;tile.image.src=url;tile.url=url;if(previous)URL.revokeObjectURL(previous)}catch(_){}finally{tile.pending=false}})()}}
function start(){stop();grid.hidden=false;active=true;observer=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting)visible.add(e.target);else visible.delete(e.target)}},{rootMargin:'150px'});sync();}
toggle.onchange=()=>{if(toggle.checked&&credentials())start();else stop()};
bar.querySelector('#wallRefresh').onclick=sync;
setInterval(()=>{if(toggle.checked&&credentials()&&!active)start();if((!toggle.checked||!credentials())&&active)stop();if(active)sync()},5000);
setInterval(poll,1100);
setInterval(()=>{if(!active)return;for(const tile of tiles.values())if(tile.pointer?.down&&tile.device?.online&&tile.device.control)sendCommand(tile,{type:'hold'})},350);
window.addEventListener('pagehide',stop);
})();
