const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),{stripTypeScriptTypes}=require('module'),{webcrypto}=require('crypto');
const token='test-registry-token-'.repeat(3),record={passcode_hash:'existing-connection-setting',calculator_config:null};
(async()=>{
 const digest=Buffer.from(await webcrypto.subtle.digest('SHA-256',new TextEncoder().encode(token))).toString('hex');let handler;
 const context={crypto:webcrypto,TextEncoder,Request,Response,Deno:{env:{get:n=>({SUPABASE_URL:'https://registry.test',SUPABASE_SERVICE_ROLE_KEY:'test-service-key'}[n])},serve:fn=>handler=fn},fetch:async(url,opts)=>{
  if(url.includes('tydesk_registry_auth'))return Response.json([{digest}]);
  if(url.includes('tydesk_connection_settings')){
   if(opts.method==='POST')Object.assign(record,JSON.parse(opts.body));
   return Response.json([record]);
  }
  throw Error('Unexpected URL '+url);
 }};
 vm.runInNewContext(stripTypeScriptTypes(fs.readFileSync(__dirname+'/supabase/functions/tydesk-device-registry/index.ts','utf8')),context);
 async function call(data,auth=true){return handler(new Request('https://edge.test',{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data)}))}
 assert.equal((await call({op:'get_calculator'},false)).status,401);
 assert.equal((await call({op:'set_calculator',calculator_config:'wrong'})).status,400);
 assert.equal((await call({op:'set_calculator',calculator_config:'ab'.repeat(48)})).status,200);
 assert.equal((await(await call({op:'get_calculator'})).json()).calculator_config,'ab'.repeat(48));
 assert.equal((await(await call({op:'get_settings'})).json()).passcode_hash,'existing-connection-setting');
 console.log('Registry authentication, validation, saved calculator settings and existing connection-setting preservation passed.');
})().catch(e=>{console.error(e);process.exit(1)});
