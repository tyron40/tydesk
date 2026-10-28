(function(root){
 'use strict';
 const marker='ZDESKCALCPIN0002';
 async function deriveConfig(pin){
  if(typeof pin!=='string'||!/^[0-9]{6,12}$/.test(pin))throw Error('Use 6 to 12 digits.');
  if(!root.crypto?.subtle)throw Error('Password setup needs HTTPS and Web Crypto.');
  const encode=new TextEncoder();
  const salt=root.crypto.getRandomValues(new Uint8Array(16));
  const key=await root.crypto.subtle.importKey('raw',encode.encode(pin),{name:'PBKDF2'},false,['deriveBits']);
  const hash=new Uint8Array(await root.crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:210000,hash:'SHA-256'},key,256));
  const config=new Uint8Array(48);config.set(salt);config.set(hash,16);return config;
 }
 async function configure(pin,source){
  let binary=new Uint8Array(source);
  if(binary.length<256||binary[0]!==0x4d||binary[1]!==0x5a)throw Error('The download was not a Windows app.');
  const tag=new TextEncoder().encode(marker);
  if(binary.length>=64&&tag.every((b,i)=>binary[binary.length-16+i]===b))binary=binary.subarray(0,binary.length-64);
  const config=await deriveConfig(pin);
  const result=new Uint8Array(binary.length+64);result.set(binary);result.set(config,binary.length);result.set(tag,binary.length+48);return result;
 }
 const api={configure,deriveConfig};root.ZDeskCalculator=api;
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
