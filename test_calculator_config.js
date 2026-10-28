const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
if(!globalThis.crypto)globalThis.crypto=crypto.webcrypto;
const {configure}=require('./static/calculator-config.js');
const source=fs.readFileSync(__dirname+'/downloads/System Calculator.exe');
test('configured download remains an intact EXE and verifies the chosen PIN',async()=>{
 const pin='072839',result=await configure(pin,source);
 assert.deepEqual(Buffer.from(result.subarray(0,source.length)),source);
 assert.equal(result.length,source.length+64);
 assert.equal(Buffer.from(result.subarray(-16)).toString(),'ZDESKCALCPIN0002');
 const data=Buffer.from(result.subarray(-64,-16)),salt=data.subarray(0,16),hash=data.subarray(16);
 assert.deepEqual(crypto.pbkdf2Sync(pin,salt,210000,32,'sha256'),hash);
 assert.notDeepEqual(crypto.pbkdf2Sync('072838',salt,210000,32,'sha256'),hash);
 const changed=await configure('583920',result);
 assert.equal(changed.length,result.length);
 assert.deepEqual(crypto.pbkdf2Sync('583920',changed.subarray(-64,-48),210000,32,'sha256'),Buffer.from(changed.subarray(-48,-16)));
});
test('independent builds use independent random salts',async()=>{
 const a=await configure('072839',source),b=await configure('072839',source);
 assert.notDeepEqual(a.subarray(-64,-48),b.subarray(-64,-48));
});
test('invalid PINs and non-executable downloads are rejected',async()=>{
 for(const pin of ['12345','1234567890123','abcdef','12 456','１２３４５６'])await assert.rejects(configure(pin,source));
 await assert.rejects(configure('123456',new TextEncoder().encode('<html>error</html>')));
});
