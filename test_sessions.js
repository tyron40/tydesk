const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const main=fs.readFileSync('templates/index.html','utf8').split('<script>')[1].split('</script>')[0];
function fixture(){const nodes=new Map(),events={},opened=[],requests=[];const node=()=>({style:{},classList:{remove(){},contains(){return false},add(){}},replaceChildren(){},append(){},removeAttribute(){},scrollIntoView(){},querySelectorAll(){return[]}});const win={opener:null,addEventListener:(k,f)=>{(events[k]??=[]).push(f)},open:(url,name)=>{const w={url,name,closed:false,focus(){},postMessage(data,origin){this.sent={data,origin}}};opened.push(w);return w}};const c={window:win,location:{origin:'https://zdesk.test',search:''},document:{querySelector:s=>{if(!nodes.has(s))nodes.set(s,node());return nodes.get(s)},querySelectorAll:()=>[],addEventListener(){},createElement:node},ZDeskControls:{Controls:class{release(){}setMode(){}}},ZDeskAudio:{Player:class{stop(){}}},URL,URLSearchParams,setInterval(){},clearInterval(){},setTimeout,console,fetch:async(url,o)=>{requests.push({url,o});return{ok:true,status:204,json:async()=>[]}}};vm.createContext(c);vm.runInContext(main,c);return{c,events,opened,requests}}
(async()=>{const a=fixture();vm.runInContext("password='test-secret';openSessionWindow({id:'one'});openSessionWindow({id:'two'})",a.c);assert.equal(a.opened.length,2);assert(a.opened.every(w=>!w.url.includes('test-secret')));const message=a.events.message[0];message({origin:'https://evil.test',source:a.opened[0],data:{type:'zdesk-session-ready'}});assert(!a.opened[0].sent);message({origin:'https://zdesk.test',source:{},data:{type:'zdesk-session-ready'}});assert(!a.opened[0].sent);message({origin:'https://zdesk.test',source:a.opened[0],data:{type:'zdesk-session-ready'}});assert.equal(a.opened[0].sent.data.password,'test-secret');assert(!a.opened[1].sent);const b=fixture();vm.runInContext("password='test-secret';selected='one';send({type:'key',key:'a'})",a.c);vm.runInContext("password='test-secret';selected='two';send({type:'key',key:'b'})",b.c);await new Promise(r=>setTimeout(r,10));assert(a.requests.at(-1).url.includes('/one/commands'));assert(b.requests.at(-1).url.includes('/two/commands'));console.log('PASS: isolated multi-device windows, no URL credentials, origin/source-checked handoff')})().catch(e=>{console.error(e);process.exit(1)});

(async()=>{
 const wake=fixture();let deviceCalls=0;
 wake.c.setTimeout=fn=>{fn();return 0};
 wake.c.fetch=async url=>{
  if(url==='/api/devices'&&deviceCalls++===0)return {ok:false,status:503};
  return {ok:true,status:200,json:async()=>url==='/api/devices'?[]:{enabled:false}};
 };
 await vm.runInContext("unlockDashboard('test-wakeup-password')",wake.c);
 assert.equal(deviceCalls,2);
 assert.equal(vm.runInContext('password',wake.c),'test-wakeup-password');
 const rejected=fixture();let denied=0;
 rejected.c.fetch=async()=>{denied++;return {ok:false,status:401}};
 await vm.runInContext("unlockDashboard('wrong-test-password')",rejected.c);
 assert.equal(denied,1);
 assert.equal(vm.runInContext('password',rejected.c),'');
 console.log('PASS: startup recovery retries safe device reads; incorrect passwords are not retried');
})().catch(e=>{console.error(e);process.exit(1)});
