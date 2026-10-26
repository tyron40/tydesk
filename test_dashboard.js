const assert=require('node:assert/strict');
global.setInterval=()=>0;
const {Controls,point,keyName}=require('./static/remote-control.js');
const {pcmWave,Player}=require('./static/system-audio.js');
function fixture(){
 const sent=[],listeners={};const el={style:{},addEventListener:(name,fn)=>listeners[name]=fn,getAttribute:()=>'/frame',focus(){},setPointerCapture(){},getBoundingClientRect:()=>({left:10,top:20,width:200,height:100})};
 const control=new Controls(el,{send:c=>sent.push(c),enabled:()=>true,advanced:()=>true,marker:{style:{},hidden:true}});
 const e=(id,x,y,type='touch',button=0)=>({pointerId:id,clientX:x,clientY:y,pointerType:type,button,preventDefault(){}});
 return{sent,control,listeners,e};
}
{
 const f=fixture();f.control.move(f.e(1,110,70,'mouse'));assert.deepEqual(f.sent[0],{type:'move',x:.5,y:.5});
 f.control.down(f.e(1,30,40,'mouse'));f.control.move(f.e(1,150,90,'mouse'));f.control.up(f.e(1,150,90,'mouse'));
 assert.deepEqual(f.sent.map(v=>v.type),['move','pointer_down','move','pointer_up']);
}
{
 const f=fixture();f.control.down(f.e(1,110,70));f.control.up(f.e(1,110,70));assert.equal(f.sent.length,1);assert.equal(f.sent[0].type,'click');assert.equal(f.sent[0].button,'left');
 f.sent.length=0;f.control.down(f.e(2,110,70));f.control.points.get(2).time-=600;f.control.up(f.e(2,110,70));assert.equal(f.sent[0].button,'right');
}
{
 const f=fixture();f.control.down(f.e(1,30,40));f.control.move(f.e(1,160,80));f.control.up(f.e(1,160,80));assert.deepEqual(f.sent.map(v=>v.type),['pointer_down','move','pointer_up']);
 f.sent.length=0;f.control.down(f.e(1,20,30));f.control.move(f.e(1,140,80));f.listeners.pointercancel();assert.equal(f.sent.at(-1).type,'release');assert.equal(f.control.points.size,0);
}
{
 const f=fixture();f.control.down(f.e(1,30,30));f.control.down(f.e(2,60,40));f.control.move(f.e(1,30,95));f.control.up(f.e(1,30,95));f.control.up(f.e(2,60,40));assert(f.sent.some(v=>v.type==='scroll'));assert(!f.sent.some(v=>v.type==='click'));
}
{
 const f=fixture();f.control.setMode('trackpad');f.control.down(f.e(1,20,30));f.control.move(f.e(1,100,50));f.control.up(f.e(1,100,50));assert(f.sent.some(v=>v.type==='move'));assert(!f.sent.some(v=>v.type==='pointer_down'));
 f.sent.length=0;f.control.setMode('pan');f.control.down(f.e(1,20,30));assert.equal(f.sent.length,0);
}
{
 assert.deepEqual(point({left:0,top:0,width:100,height:100},-20,150),{x:0,y:1});
 assert.equal(keyName({key:'!',code:'Digit1'}),'1');assert.equal(keyName({key:'A',code:'KeyA'}),'a');assert.equal(keyName({key:'ArrowLeft'}),'left');
 const f=fixture();f.listeners.keydown({key:'Control',preventDefault(){}});f.listeners.keydown({key:'c',code:'KeyC',preventDefault(){}});f.listeners.blur();assert.equal(f.sent.at(-1).type,'release');assert.equal(f.control.keys.size,0);
}
{
 const f=fixture();f.control.setMode('trackpad');f.control.down(f.e(1,30,40));f.control.move(f.e(1,31,41));assert.equal(f.sent.length,0,'Small touch jitter should not move the pointer');
 f.control.points.get(1).time-=600;f.control.move(f.e(1,70,50));f.control.up(f.e(1,70,50));
 assert.deepEqual(f.sent.map(v=>v.type),['pointer_down','move','pointer_up'],'Hold then move drags in trackpad mode');
}
function wave(){const b=Buffer.alloc(44+4800*4);b.write('RIFF');b.writeUInt32LE(b.length-8,4);b.write('WAVEfmt ',8);b.writeUInt32LE(16,16);b.writeUInt16LE(1,20);b.writeUInt16LE(2,22);b.writeUInt32LE(24000,24);b.writeUInt32LE(96000,28);b.writeUInt16LE(4,32);b.writeUInt16LE(16,34);b.write('data',36);b.writeUInt32LE(b.length-44,40);for(let i=0;i<4800;i++){const v=Math.round(Math.sin(i/24000*2*Math.PI*440)*10000);b.writeInt16LE(v,44+i*4);b.writeInt16LE(v,46+i*4)}return b}
(async()=>{
 const bytes=wave(),pcm=pcmWave(bytes);assert.equal(pcm.frames,4800);assert(pcm.peak>.3);assert.throws(()=>pcmWave(bytes.subarray(0,60)));
 let stopped=0,closed=0;
 global.AudioContext=class{constructor(){this.state='suspended';this.currentTime=0;this.destination={}}async resume(){this.state='running'}createGain(){return{gain:{value:1},connect(){}}}createBuffer(n,f){const c=[new Float32Array(f),new Float32Array(f)];return{duration:f/24000,getChannelData:i=>c[i]}}createBufferSource(){return{connect(){},disconnect(){},start(){},stop(){stopped++}}}async close(){closed++}};
 const player=new Player();await player.start();assert.equal(player.context.state,'running');player.push(bytes.toString('base64'));assert.equal(player.sources.size,1);player.setVolume(.5);assert.equal(player.gain.gain.value,.5);player.stop();assert.equal(stopped,1);assert.equal(closed,1);assert.equal(player.context,null);
 console.log('PASS: mouse movement/drag, touch tap/drag/right-click/two-finger scroll, trackpad/pan, key release, PCM tone playback/resume/volume/stop');
})().catch(e=>{console.error(e);process.exit(1)});

{
 const vm=require('node:vm'),fs=require('node:fs');
 function browserOptions(screenAvailable){
  const nodes=new Map(),node=()=>({checked:false,disabled:false});let prompts=0;
  const c={document:{querySelector:id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)},createElement:()=>({getContext:()=>({})})},navigator:{mediaDevices:{getDisplayMedia:screenAvailable?()=>{prompts++}:undefined,getUserMedia:()=>{prompts++}}},window:{addEventListener(){}},Map,Set,console};
  vm.createContext(c);vm.runInContext(fs.readFileSync('static/browser-companion.js','utf8'),c);
  vm.runInContext("$('#selectAll').onclick()",c);
  assert.equal(nodes.get('#screenPermission').checked,screenAvailable);assert(nodes.get('#micPermission').checked);assert(nodes.get('#filePermission').checked);assert.equal(prompts,0,'Select all must not request permissions or start capture');
  nodes.get('#micPermission').checked=false;vm.runInContext("device={id:'active'};$('#selectAll').onclick()",c);assert.equal(nodes.get('#micPermission').checked,false,'Active sharing options remain locked');
 }
 browserOptions(true);browserOptions(false);
 console.log('PASS: browser Select all respects screen support and does not start capture or request permissions');
}
