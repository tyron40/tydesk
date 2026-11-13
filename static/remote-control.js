/* Pointer Events: one input path for mouse, pen and touch. */
(function(root){
'use strict';
const clamp=v=>Math.max(0,Math.min(1,v));
function point(rect,x,y){return{x:clamp((x-rect.left)/Math.max(1,rect.width)),y:clamp((y-rect.top)/Math.max(1,rect.height))}}
function keyName(e){
 const names={Enter:'enter',Tab:'tab',Escape:'esc',Backspace:'backspace',Delete:'delete',Home:'home',End:'end',PageUp:'pageup',PageDown:'pagedown',ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',Shift:'shift',Control:'ctrl',Alt:'alt',Meta:'win',CapsLock:'capslock',Insert:'insert',' ':'space'};
 const physical={Minus:'-',Equal:'=',BracketLeft:'[',BracketRight:']',Semicolon:';',Quote:"'",Comma:',',Period:'.',Slash:'/',Backslash:'\\',Backquote:'`'};
 if(names[e.key])return names[e.key];if(/^Key[A-Z]$/.test(e.code||''))return e.code.slice(3).toLowerCase();if(/^Digit[0-9]$/.test(e.code||''))return e.code.slice(5);if(physical[e.code])return physical[e.code];if(/^F([1-9]|1[0-2])$/.test(e.key))return e.key.toLowerCase();
 if(typeof e.key==='string'&&e.key.length===1&&/^[\x20-\x7e]$/.test(e.key))return e.key.toLowerCase();return null;
}
class Controls{
 constructor(el,{send,enabled,advanced,marker}){
  this.el=el;this.send=send;this.enabled=enabled;this.advanced=advanced;this.marker=marker;this.points=new Map();this.keys=new Set();this.cur={x:.5,y:.5};this.mode='direct';this.drag=false;this.multi=false;this.wheel=0;
  el.addEventListener('pointerdown',e=>this.down(e));el.addEventListener('pointermove',e=>this.move(e));el.addEventListener('pointerup',e=>this.up(e));el.addEventListener('pointercancel',()=>this.release());el.addEventListener('lostpointercapture',()=>{if(this.points.size)this.release()});
  el.addEventListener('contextmenu',e=>e.preventDefault());el.addEventListener('wheel',e=>{if(!this.active())return;e.preventDefault();this.wheel+=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?300:1);if(Math.abs(this.wheel)>=30){this.emit({type:'scroll',amount:this.wheel>0?-1:1});this.wheel=0}},{passive:false});
  el.addEventListener('keydown',e=>{if(!this.active())return;const key=keyName(e);if(!key)return;e.preventDefault();if(!this.advanced()){if(!e.repeat)this.emit({type:'key',key});return}if(!this.keys.has(key)){this.keys.add(key);this.emit({type:'key_down',key})}});
  el.addEventListener('keyup',e=>{const key=keyName(e);if(this.keys.delete(key)){e.preventDefault();this.emit({type:'key_up',key})}});
  el.addEventListener('blur',()=>this.release());
  this.heartbeat=setInterval(()=>{if(this.drag||this.keys.size)this.emit({type:'hold'})},300);
 }
 active(){return this.enabled()&&this.mode!=='pan'}
 emit(c){if(this.enabled())this.send(c)}
 position(e){return point(this.el.getBoundingClientRect(),e.clientX,e.clientY)}
 locate(p){this.cur=p;if(this.marker){this.marker.style.left=(p.x*100)+'%';this.marker.style.top=(p.y*100)+'%';this.marker.hidden=false}}
 down(e){
  if(!this.active()||!this.el.getAttribute('src')||![0,2].includes(e.button)&&e.pointerType==='mouse')return;
  e.preventDefault();if(this.mode!=='finger')this.el.focus({preventScroll:true});this.el.setPointerCapture(e.pointerId);
  const p=this.position(e);this.points.set(e.pointerId,{x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,start:p,time:Date.now(),button:e.button===2?'right':'left',touch:e.pointerType==='touch'});
  if(this.points.size>1){if(this.drag)this.emit({type:'release'});this.drag=false;this.multi=true;this.scrollY=this.centroid();return}
  this.multi=false;
  if(e.pointerType!=='touch'&&this.advanced()&&this.mode!=='finger'){this.drag=true;this.locate(p);this.emit({type:'pointer_down',...p,button:e.button===2?'right':'left'})}
 }
 centroid(){return [...this.points.values()].reduce((sum,p)=>sum+p.y,0)/this.points.size}
 move(e){
  if(!this.active()||!this.el.getAttribute('src'))return;
  const old=this.points.get(e.pointerId),p=this.position(e);
  if(!old){if(e.pointerType==='mouse'&&this.advanced()){this.locate(p);this.emit({type:'move',...p})};return}
  e.preventDefault();const dx=e.clientX-old.x,dy=e.clientY-old.y;old.x=e.clientX;old.y=e.clientY;
  if(this.mode==='finger'){if(this.points.size>1)return;if(Math.hypot(e.clientX-old.startX,e.clientY-old.startY)>4&&!this.drag){this.drag=true;this.emit({type:'pointer_down',...old.start,button:'left'})}if(this.drag)this.emit({type:'move',...p});return}
  if(this.multi){if(this.points.size>=2){const y=this.centroid();if(Math.abs(y-this.scrollY)>=18){this.emit({type:'scroll',amount:y>this.scrollY?1:-1});this.scrollY=y}}return}
  if(!this.advanced())return;
  const distance=Math.hypot(e.clientX-old.startX,e.clientY-old.startY);
  if(old.touch&&this.mode==='trackpad'){
   if(distance<4)return;
   if(!old.moved){old.moved=true;old.trackDrag=Date.now()-old.time>500;if(old.trackDrag){this.drag=true;this.emit({type:'pointer_down',...this.cur,button:'left'})}}
   const r=this.el.getBoundingClientRect();this.locate({x:clamp(this.cur.x+dx/r.width*1.4),y:clamp(this.cur.y+dy/r.height*1.4)});this.emit({type:'move',...this.cur});return;
  }
  if(old.touch&&!this.drag&&distance>7){this.drag=true;this.emit({type:'pointer_down',...old.start,button:'left'})}
  if(this.drag||!old.touch){this.locate(p);this.emit({type:'move',...p})}
 }
 up(e){
  const old=this.points.get(e.pointerId);if(!old)return;e.preventDefault();this.points.delete(e.pointerId);
  if(this.multi){if(!this.points.size){this.multi=false;this.drag=false}return}
  const p=this.mode==='trackpad'&&old.touch?this.cur:this.position(e),distance=Math.hypot(e.clientX-old.startX,e.clientY-old.startY);
  if(this.drag&&this.advanced())this.emit({type:'pointer_up',...p,button:old.button});
  else if(!old.touch||distance<8){this.locate(p);this.emit({type:'click',...p,button:old.touch&&Date.now()-old.time>500?'right':old.button})}
  if(this.mode==='finger'&&this.marker)this.marker.hidden=true;
  this.drag=false;
 }
 release(){if(this.points.size||this.keys.size||this.drag)this.emit({type:'release'});this.points.clear();this.keys.clear();this.drag=false;this.multi=false}
 setMode(mode){this.release();this.mode=mode;if(mode==='finger'&&this.marker)this.marker.hidden=true;this.el.style.touchAction=mode==='pan'?'auto':'none'}
}
root.ZDeskControls={Controls,point,keyName};if(typeof module!=='undefined')module.exports=root.ZDeskControls;
})(typeof window!=='undefined'?window:globalThis);
