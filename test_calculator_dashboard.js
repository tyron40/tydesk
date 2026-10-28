const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync(__dirname+'/templates/index.html','utf8');
const start=html.indexOf('function clearCalculatorDownload'),end=html.indexOf("$('#auth').onsubmit",start),fields={};
const el=id=>fields[id]??={value:'',textContent:'',hidden:false,disabled:false,focus(){},reset(){el('#calculatorPin').value='';el('#calculatorConfirm').value=''}};
const calls=[];let saved=false;
const ctx={$:el,dashboardUnlocked:false,password:'',ZDeskCalculator:{deriveConfig:async()=>new Uint8Array(48).fill(0xab)},api:async(path,method,body)=>{calls.push([path,method,body]);if(method==='PUT'){assert.equal(body.config,'ab'.repeat(48));assert(!JSON.stringify(body).includes('072839'));saved=true}return{configured:saved}}};
vm.createContext(ctx);vm.runInContext(html.slice(start,end),ctx);
(async()=>{
 const submit=()=>el('#calculatorForm').onsubmit({preventDefault(){}});
 el('#calculatorPin').value=el('#calculatorConfirm').value='072839';await submit();assert.equal(calls.length,0);
 ctx.dashboardUnlocked=true;ctx.password='test-owner-session';await ctx.refreshCalculator();assert.equal(el('#calculatorForm').hidden,false);
 await submit();assert.equal(el('#calculatorForm').hidden,true);assert.equal(el('#calculatorPin').value,'');assert.equal(el('#calculatorChange').hidden,false);
 await ctx.refreshCalculator();assert.equal(el('#calculatorForm').hidden,true,'Saved setting survives refresh without another password prompt');
 assert(html.includes('href="/download/system-calculator" download="System Calculator.exe"'));assert(!html.slice(start,end).includes('createObjectURL'));
 console.log('Dashboard saved-once status, hidden setup after saving, hash-only request and permanent download link passed.');
})().catch(e=>{console.error(e);process.exit(1)});
