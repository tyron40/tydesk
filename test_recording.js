const assert=require('node:assert/strict');
const {Recording}=require('./static/audio-recorder.js');
let last,stopped=0,disconnected=0,connected=0;
global.MediaRecorder=class{
 static isTypeSupported(type){return type==='audio/mp4'}
 constructor(stream,options){this.stream=stream;this.mimeType=options?.mimeType||'audio/webm';this.state='inactive';last=this}
 start(ms){assert.equal(ms,1000);this.state='recording'}
 stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable({data:new Blob(['final'],{type:this.mimeType})});this.onstop()})}
};
function fixture(){const states=[],saved=[];const context={state:'running',createMediaStreamDestination:()=>({stream:{getTracks:()=>[{stop(){stopped++}}]}})};const source={connect(){connected++},disconnect(){disconnected++}};return{states,saved,context,source,r:new Recording({onState:(...s)=>states.push(s),onReady:(...s)=>saved.push(s)})}}
(async()=>{
 const f=fixture();assert.throws(()=>f.r.start(null,f.source),/listening/);f.r.start(f.context,f.source);assert(f.r.active);assert.equal(f.states[0][0],'recording');assert.throws(()=>f.r.start(f.context,f.source),/Finish/);
 last.ondataavailable({data:new Blob(['first'])});f.r.stop();assert(f.r.finishing);assert.equal(f.saved.length,0,'Wait for final dataavailable before download');f.r.stop();await Promise.resolve();assert.equal(await f.saved[0][0].text(),'firstfinal');assert.equal(f.saved[0][1],'m4a');assert(!f.r.active);assert(!f.r.finishing);assert.equal(stopped,1);assert.equal(disconnected,1);
 f.r.start(f.context,f.source);f.r.stop('Duration limit');await Promise.resolve();assert.equal(f.states.at(-1)[1],'Duration limit');assert.equal(f.saved.length,2);
 const bounded=fixture();bounded.r.maxBytes=6;bounded.r.start(bounded.context,bounded.source);last.ondataavailable({data:new Blob(['1234'])});last.ondataavailable({data:new Blob(['789'])});await Promise.resolve();assert.equal(await bounded.saved[0][0].text(),'1234');assert(bounded.saved[0][0].size<=6);assert.match(bounded.states.at(-1)[1],/memory/);
 global.MediaRecorder=undefined;assert.throws(()=>fixture().r.start(f.context,f.source),/unavailable/);
 console.log('PASS: playback graph recording, MP4 selection, final packet saved, repeated stop/start, memory limit, cleanup, unsupported browser');
})().catch(e=>{console.error(e);process.exitCode=1});
