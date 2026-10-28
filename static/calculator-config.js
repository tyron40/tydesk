(function(root){
 'use strict';
 const marker='ZDESKCALCPIN0002';
 async function configure(pin,source){
  if(typeof pin!=='string'||!/^[0-9]{6,12}$/.test(pin))throw Error('Use 6 to 12 digits.');
  if(!root.crypto?.subtle)throw Error('PIN setup needs HTTPS and a browser with Web Crypto.');
  let binary=new Uint8Array(source);
  if(binary.length<256||binary[0]!==0x4d||binary[1]!==0x5a)throw Error('The download was not a Windows app. Try again shortly.');
  const encode=new TextEncoder(),tag=encode.encode(marker);
  // Replace an earlier configuration instead of growing the file indefinitely.
  if(binary.length>=64&&tag.every((b,i)=>binary[binary.length-16+i]===b))binary=binary.subarray(0,binary.length-64);
  const salt=root.crypto.getRandomValues(new Uint8Array(16));
  const key=await root.crypto.subtle.importKey('raw',encode.encode(pin),{name:'PBKDF2'},false,['deriveBits']);
  const hash=new Uint8Array(await root.crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:210000,hash:'SHA-256'},key,256));
  const result=new Uint8Array(binary.length+64);result.set(binary);result.set(salt,binary.length);result.set(hash,binary.length+16);result.set(tag,binary.length+48);return result;
 }
 const api={configure};root.ZDeskCalculator=api;
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(globalThis);
