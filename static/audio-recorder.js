(function(root){
'use strict';
// Records only the remote playback graph. Never requests this browser's microphone.
class Recording{
 constructor({onState=()=>{},onReady=()=>{}}={}){this.onState=onState;this.onReady=onReady;this.recorder=null;this.finishing=false;this.maxBytes=64*1024*1024;this.maxMs=60*60*1000}
 get active(){return !!this.recorder}
 start(context,source){
  if(this.active||this.finishing)throw Error('Finish the current recording first');
  if(!context||context.state!=='running')throw Error('Start listening before recording');
  if(!root.MediaRecorder||!context.createMediaStreamDestination)throw Error('Audio recording is unavailable in this browser');
  const destination=context.createMediaStreamDestination();let recorder;
  try{
   const types=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus'];
   for(const mimeType of types){if(!root.MediaRecorder.isTypeSupported(mimeType))continue;try{recorder=new root.MediaRecorder(destination.stream,{mimeType,audioBitsPerSecond:128000});break}catch{}}
   if(!recorder)recorder=new root.MediaRecorder(destination.stream);
  }catch(e){destination.stream.getTracks().forEach(t=>t.stop());throw e}
  let chunks=[],bytes=0,reason='';this.stopReason='';this.recorder=recorder;this.started=Date.now();
  const cleanup=()=>{clearTimeout(this.timer);try{source.disconnect(destination)}catch{}destination.stream.getTracks().forEach(t=>t.stop());this.recorder=null;this.finishing=false};
  recorder.ondataavailable=event=>{
   if(event.data.size){if(bytes+event.data.size>this.maxBytes){reason='Recording reached the memory limit';this.stop(reason)}else{chunks.push(event.data);bytes+=event.data.size}}
   if(!this.finishing)this.onState('recording',Math.floor((Date.now()-this.started)/1000));
  };
  recorder.onerror=()=>{reason='Recording interrupted by the browser';this.stop(reason)};
  recorder.onstop=()=>{
   const mime=recorder.mimeType||chunks.find(c=>c.type)?.type||'application/octet-stream';
   const blob=new Blob(chunks,{type:mime});chunks=[];cleanup();
   if(blob.size)this.onReady(blob,/mp4/i.test(mime)?'m4a':/ogg/i.test(mime)?'ogg':/webm/i.test(mime)?'webm':'audio');
   this.onState(blob.size?'ready':'error',reason||this.stopReason||(blob.size?'Recording ready to download':'No audio was recorded'));
  };
  try{source.connect(destination);recorder.start(1000)}catch(e){cleanup();throw e}
  this.timer=setTimeout(()=>this.stop('Recording reached the one-hour limit'),this.maxMs);
  this.onState('recording',0);
 }
 stop(reason=''){
  if(!this.recorder||this.finishing)return;
  this.stopReason=reason;this.finishing=true;clearTimeout(this.timer);this.onState('finishing',reason||'Preparing recording…');
  if(this.recorder.state!=='inactive')this.recorder.stop();
 }
}
root.ZDeskRecording={Recording};if(typeof module!=='undefined')module.exports=root.ZDeskRecording;
})(typeof window!=='undefined'?window:globalThis);
