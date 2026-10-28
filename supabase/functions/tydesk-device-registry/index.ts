// Dedicated backend-only device registry. No raw enrollment tokens or screen data.
const url=Deno.env.get('SUPABASE_URL')!;
function secret(){
 const keys=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS')||'{}');
 return keys.default||Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||Deno.env.get('SUPABASE_SECRET_KEY');
}
async function rest(path:string,method='GET',body?:unknown){
 const key=secret();if(!key)throw Error('Missing backend key');
 const r=await fetch(url+'/rest/v1/'+path,{method,headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json',Prefer:'resolution=merge-duplicates,return=representation'},body:body===undefined?undefined:JSON.stringify(body)});
 if(!r.ok)throw Error('Registry database unavailable');
 const text=await r.text();return text?JSON.parse(text):null;
}
function equal(a:string,b:string){if(a.length!==b.length)return false;let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0}
Deno.serve(async(req:Request)=>{
 if(req.method!=='POST')return Response.json({error:'Method not allowed'},{status:405});
 const token=(req.headers.get('Authorization')||'').replace(/^Bearer /,'');
 if(token.length<40||token.length>200)return Response.json({error:'Unauthorized'},{status:401});
 try{
  const rows=await rest('tydesk_registry_auth?id=eq.primary&select=digest');
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token));
  const digest=Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');
  if(!rows?.[0]||!equal(digest,rows[0].digest))return Response.json({error:'Unauthorized'},{status:401});
  const raw=await req.text();if(raw.length>4096)return Response.json({error:'Too large'},{status:413});
  const data=JSON.parse(raw);
  if(data.op==='list')return Response.json(await rest('tydesk_saved_devices?select=id,token,name&order=created_at.asc&limit=100'));
  if(data.op==='get_settings'){
   const rows=await rest('tydesk_connection_settings?id=eq.primary&select=passcode_hash');
   return Response.json({passcode_hash:rows?.[0]?.passcode_hash||null});
  }
  if(data.op==='set_settings'){
   if(data.passcode_hash!==null && !/^pbkdf2_sha256\$260000\$[a-f0-9]{32}\$[a-f0-9]{64}$/.test(data.passcode_hash||''))return Response.json({error:'Invalid setting'},{status:400});
   await rest('tydesk_connection_settings','POST',{id:'primary',passcode_hash:data.passcode_hash});return Response.json({ok:true});
  }
  if(data.op==='get_calculator'){
   const rows=await rest('tydesk_connection_settings?id=eq.primary&select=calculator_config');
   return Response.json({calculator_config:rows?.[0]?.calculator_config||null});
  }
  if(data.op==='set_calculator'){
   if(typeof data.calculator_config!=='string'||!/^[a-f0-9]{96}$/.test(data.calculator_config))return Response.json({error:'Invalid calculator setting'},{status:400});
   await rest('tydesk_connection_settings','POST',{id:'primary',calculator_config:data.calculator_config});return Response.json({ok:true});
  }
  if(!/^[a-f0-9]{24}$/.test(data.id||''))return Response.json({error:'Invalid device ID'},{status:400});
  if(data.op==='register'){
   if(!/^[a-f0-9]{64}$/.test(data.token||'')||typeof data.name!=='string'||data.name.length<1||data.name.length>80)return Response.json({error:'Invalid device'},{status:400});
   await rest('tydesk_saved_devices','POST',{id:data.id,token:data.token,name:data.name});return Response.json({ok:true});
  }
  if(data.op==='revoke'){await rest('tydesk_saved_devices?id=eq.'+data.id,'DELETE');return Response.json({ok:true})}
  return Response.json({error:'Invalid operation'},{status:400});
 }catch{return Response.json({error:'Registry temporarily unavailable'},{status:503})}
});

