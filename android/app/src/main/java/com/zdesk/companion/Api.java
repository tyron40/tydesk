package com.zdesk.companion;
import java.net.*;
import java.io.*;
import java.util.*;
final class Api {
 final String url,token;
 Api(String url,String token){URI u=URI.create(url);if(!"https".equals(u.getScheme())||u.getHost()==null||u.getUserInfo()!=null||u.getQuery()!=null||u.getFragment()!=null||!(u.getPath().isEmpty()||u.getPath().equals("/")))throw new IllegalArgumentException("Enter an HTTPS server address without a path");this.url=url.replaceAll("/$","");this.token=token;}
 static final class Failure extends IOException {final int code;Failure(int code){super("Server returned "+code);this.code=code;}}
 byte[] call(String path,String method,byte[] body,Map<String,String> headers) throws Exception {
  HttpURLConnection c=(HttpURLConnection)new URL(url+path).openConnection();c.setInstanceFollowRedirects(false);c.setConnectTimeout(8000);c.setReadTimeout(15000);c.setRequestMethod(method);
  if(token!=null)c.setRequestProperty("Authorization","Bearer "+token);if(headers!=null)for(Map.Entry<String,String> h:headers.entrySet())c.setRequestProperty(h.getKey(),h.getValue());
  try{if(body!=null){c.setDoOutput(true);c.setFixedLengthStreamingMode(body.length);try(OutputStream out=c.getOutputStream()){out.write(body);}}int status=c.getResponseCode();if(status<200||status>=300)throw new Failure(status);try(InputStream in=c.getInputStream()){return read(in,21*1024*1024);}}finally{c.disconnect();}
 }
 String json(String path,String method,Object value) throws Exception{return new String(call(path,method,value==null?null:value.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8),Collections.singletonMap("Content-Type","application/json")),java.nio.charset.StandardCharsets.UTF_8);}
 static byte[] read(InputStream in,int limit)throws IOException{ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[16384];int n;while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IOException("File exceeds 20 MB limit");out.write(buffer,0,n);}return out.toByteArray();}
}
