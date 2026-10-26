(function(root){
'use strict';
function pcmWave(bytes){
 const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),str=(o,n)=>String.fromCharCode(...bytes.subarray(o,o+n));
 if(bytes.length<44||str(0,4)!=='RIFF'||str(8,4)!=='WAVE')throw Error('Invalid audio frame');
 let fmt=null,data=null;
 for(let o=12;o+8<=bytes.length;){const size=v.getUint32(o+4,true),start=o+8;if(start+size>bytes.length)throw Error('Truncated audio frame');const tag=str(o,4);if(tag==='fmt '){if(size<16)throw Error('Invalid format');fmt={type:v.getUint16(start,true),channels:v.getUint16(start+2,true),rate:v.getUint32(start+4,true),bits:v.getUint16(start+14,true)}}if(tag==='data')data={start,size};o=start+size+(size%2)}
 if(!fmt||!data||fmt.type!==1||fmt.channels!==2||fmt.rate!==24000||fmt.bits!==16||!data.size||data.size%4)throw Error('Unsupported audio frame');
 const frames=data.size/4;if(frames>48000)throw Error('Audio frame too large');const channels=[new Float32Array(frames),new Float32Array(frames)];let peak=0;
 for(let i=0;i<frames;i++)for(let c=0;c<2;c++){const value=v.getInt16(data.start+i*4+c*2,true)/32768;channels[c][i]=value;peak=Math.max(peak,Math.abs(value))}return{channels,frames,rate:24000,peak};
}
class Player{
 constructor(){this.context=null;this.sources=new Set();this.next=0;this.volume=1;this.generation=0;this.delay=.8;this.underruns=0;this.started=false}
 async start(){
  if(!this.context){const Context=root.AudioContext||root.webkitAudioContext;if(!Context)throw Error('Audio playback is unavailable in this browser');this.context=new Context();this.gain=this.context.createGain();this.gain.gain.value=this.volume;this.gain.connect(this.context.destination);this.generation++}
  await this.context.resume();if(this.context.state!=='running')throw Error('Tap Listen again to allow audio playback');
 }
 setVolume(value){this.volume=Math.max(0,Math.min(2,Number(value)));if(this.gain)this.gain.gain.value=this.volume}
 push(base64){
  const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0)),pcm=pcmWave(bytes),ctx=this.context;if(!ctx||ctx.state!=='running')return null;
  if(this.next>ctx.currentTime+4)return null;
  const buffer=ctx.createBuffer(2,pcm.frames,pcm.rate);pcm.channels.forEach((c,i)=>buffer.getChannelData(i).set(c));
  const source=ctx.createBufferSource();source.buffer=buffer;source.connect(this.gain);this.sources.add(source);source.onended=()=>{this.sources.delete(source);source.disconnect()};
  if(!this.started||this.next<ctx.currentTime+.015){if(this.started){this.underruns++;this.delay=Math.min(1.4,this.delay+.2)}this.next=ctx.currentTime+this.delay;this.started=true}source.start(this.next);this.next+=buffer.duration;return pcm;
 }
 reset(){for(const s of this.sources){try{s.stop();s.disconnect()}catch{}}this.sources.clear();this.next=0;this.started=false;this.delay=.8;this.underruns=0}
 stop(){this.generation++;this.reset();if(this.context)this.context.close().catch(()=>{});this.context=null}
}
function recentChunks(chunks,seconds=1){let duration=0,start=chunks.length;while(start>0&&duration<seconds){start--;const bytes=Uint8Array.from(atob(chunks[start].wav),c=>c.charCodeAt(0));duration+=pcmWave(bytes).frames/24000}return chunks.slice(start)}
root.ZDeskAudio={Player,pcmWave,recentChunks};if(typeof module!=='undefined')module.exports=root.ZDeskAudio;
})(typeof window!=='undefined'?window:globalThis);
