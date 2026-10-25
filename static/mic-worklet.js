class ZDeskMic extends AudioWorkletProcessor{
 constructor(){super();this.buffer=new Float32Array(Math.round(sampleRate*.2));this.offset=0}
 process(inputs){const channel=inputs[0]?.[0];if(channel)for(const value of channel){this.buffer[this.offset++]=value;if(this.offset===this.buffer.length){this.port.postMessage({samples:this.buffer,rate:sampleRate},[this.buffer.buffer]);this.buffer=new Float32Array(Math.round(sampleRate*.2));this.offset=0}}return true}
}
registerProcessor('zdesk-mic',ZDeskMic);
