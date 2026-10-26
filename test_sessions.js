const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const main=fs.readFileSync('templates/index.html','utf8').split('<script>')[1].split('</script>')[0];
function fixture(){const nodes=new Map(),events={},opened=[],requests=[];const node=()=>({style:{},classList:{values:new Set(),remove(v){this.values.delete(v)},contains(v){return this.values.has(v)},add(v){this.values.add(v)},toggle(v,on){if(on)this.values.add(v);else this.values.delete(v)}},replaceChildren(){},append(){},removeAttribute(){},setAttribute(){},scrollIntoView(){},querySelectorAll(){return[]}});const win={opener:null,addEventListener:(k,f)=>{(events[k]??=[]).push(f)},open:(url,name)=>{const w={url,name,closed:false,focus(){},postMessage(data,origin){this.sent={data,origin}}};opened.push(w);return w}};const c={window:win,location:{origin:'https://zdesk.test',search:''},document:{body:node(),querySelector:s=>{if(!nodes.has(s))nodes.set(s,node());return nodes.get(s)},querySelectorAll:()=>[],addEventListener(){},createElement:node},ZDeskControls:{Controls:class{release(){}setMode(){}}},ZDeskAudio:{Player:class{stop(){}}},URL,URLSearchParams,setInterval(){},clearInterval(){},setTimeout,console,fetch:async(url,o)=>{requests.push({url,o});return{ok:true,status:204,json:async()=>[]}}};vm.createContext(c);vm.runInContext(main,c);return{c,events,opened,requests}}
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

(async()=>{
 const f=fixture();await vm.runInContext("$('#fullscreen').onclick()",f.c);
 assert(vm.runInContext("$('#viewer').classList.contains('focus-mode')",f.c),'Fullscreen fallback must work without native API');
 assert(vm.runInContext("document.body.classList.contains('session-expanded')",f.c));
 vm.runInContext("$('#screen').naturalWidth=1920;$('#screen').naturalHeight=1080;$('#screenViewport').clientWidth=390;$('#screenViewport').clientHeight=650;$('#screenScale').value='fit';scaleScreen()",f.c);
 assert.equal(vm.runInContext("$('#screenStage').style.width",f.c),'390px');
 vm.runInContext("$('#screenViewport').clientWidth=844;$('#screenViewport').clientHeight=300;scaleScreen()",f.c);
 assert.equal(vm.runInContext("$('#screenStage').style.width",f.c),(300*1920/1080)+'px');
 await vm.runInContext("$('#fullscreen').onclick()",f.c);
 assert(!vm.runInContext("document.body.classList.contains('session-expanded')",f.c));
 console.log('PASS: mobile fullscreen fallback, orientation resize fit, page scrolling restored');
})().catch(e=>{console.error(e);process.exit(1)});
