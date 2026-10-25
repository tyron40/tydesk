package com.zdesk.companion;
import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.graphics.*;
import android.hardware.display.*;
import android.media.*;
import android.media.projection.*;
import android.os.*;
import android.util.DisplayMetrics;
import android.view.WindowManager;
import android.net.Uri;
import android.database.Cursor;
import android.provider.OpenableColumns;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
public class ShareService extends Service {
 static volatile boolean active=false,projectionActive=false,allowControl=false;
 static volatile int deviceWidth=1080,deviceHeight=1920;
 volatile boolean running=false;boolean mic,screen,files;Api api;String id,url;JSONObject enrollment;
 MediaProjection projection;VirtualDisplay display;ImageReader reader;HandlerThread captureThread;Handler capture;final Handler main=new Handler(Looper.getMainLooper());
 final AtomicReference<byte[]> frame=new AtomicReference<>(),audio=new AtomicReference<>();
 final ExecutorService workers=Executors.newFixedThreadPool(4);
 long encodedAt=0;int width,height,density;Map<String,Uri> shares=new HashMap<>();Set<String> finished=new HashSet<>();
 final String channel="zdesk-sharing";
 public IBinder onBind(Intent intent){return null;}
 public int onStartCommand(Intent intent,int flags,int startId){
  if(intent==null){stopSelf();return START_NOT_STICKY;}if("stop".equals(intent.getAction())){stopSelf();return START_NOT_STICKY;}if(running)return START_NOT_STICKY;
  screen=intent.getBooleanExtra("screen",true);mic=intent.getBooleanExtra("mic",false);files=getSharedPreferences("options",0).getBoolean("files",false);
  ((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).createNotificationChannel(new NotificationChannel(channel,"ZDesk active sharing",NotificationManager.IMPORTANCE_LOW));
  int types=screen?ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION:0;if(mic)types|=ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;if(types==0)types=ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC;
  if(Build.VERSION.SDK_INT>=29)startForeground(42,notification("Starting sharing…"),types);else startForeground(42,notification("Starting sharing…"));
  running=true;active=true;url=intent.getStringExtra("url");String code=intent.getStringExtra("code");
  try{if(screen){MediaProjectionManager manager=(MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);projection=manager.getMediaProjection(intent.getIntExtra("result",0),(Intent)intent.getParcelableExtra("data"));if(projection==null)throw new IllegalStateException("Approve screen sharing first");captureThread=new HandlerThread("ZDesk capture");captureThread.start();capture=new Handler(captureThread.getLooper());projection.registerCallback(new MediaProjection.Callback(){public void onStop(){main.post(()->{notice("Screen sharing ended. Open ZDesk to approve a new session.");stopSelf();});}public void onCapturedContentResize(int w,int h){if(capture!=null)capture.post(()->resize(w,h));}},main);DisplayMetrics metrics=new DisplayMetrics();((WindowManager)getSystemService(WINDOW_SERVICE)).getDefaultDisplay().getRealMetrics(metrics);density=metrics.densityDpi;deviceWidth=metrics.widthPixels;deviceHeight=metrics.heightPixels;resize(deviceWidth,deviceHeight);projectionActive=true;}}
  catch(Exception e){notice("Cannot start screen sharing: "+e.getClass().getSimpleName());stopSelf();return START_NOT_STICKY;}
  workers.execute(()->connect(code));return START_NOT_STICKY;
 }
 Notification notification(String text){PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,ShareService.class).setAction("stop"),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);return new Notification.Builder(this,channel).setContentTitle("ZDesk · sharing active").setContentText(text).setSmallIcon(R.drawable.zdesk_notification).setContentIntent(open).setOngoing(true).addAction(new Notification.Action.Builder(android.R.drawable.ic_menu_close_clear_cancel,"Stop sharing",stop).build()).build();}
 void notice(String text){getSharedPreferences("options",0).edit().putString("status",text).apply();if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED)return;if(running)((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(42,notification(text));}
 void resize(int w,int h){if(!running||projection==null||w<=0||h<=0)return;deviceWidth=w;deviceHeight=h;float scale=Math.min(1,1200f/Math.max(w,h));int nw=Math.max(2,(int)(w*scale)),nh=Math.max(2,(int)(h*scale));if(reader!=null&&nw==width&&nh==height)return;width=nw;height=nh;
  ImageReader next=ImageReader.newInstance(width,height,PixelFormat.RGBA_8888,2);ImageReader old=reader;reader=next;
  next.setOnImageAvailableListener(r->{try(Image image=r.acquireLatestImage()){if(image==null||!running)return;if(android.os.SystemClock.elapsedRealtime()-encodedAt<300)return;encodedAt=android.os.SystemClock.elapsedRealtime();Image.Plane p=image.getPlanes()[0];int padded=image.getWidth()+(p.getRowStride()-p.getPixelStride()*image.getWidth())/p.getPixelStride();Bitmap full=Bitmap.createBitmap(padded,image.getHeight(),Bitmap.Config.ARGB_8888);full.copyPixelsFromBuffer(p.getBuffer());Bitmap cropped=Bitmap.createBitmap(full,0,0,image.getWidth(),image.getHeight());ByteArrayOutputStream out=new ByteArrayOutputStream();cropped.compress(Bitmap.CompressFormat.JPEG,55,out);frame.set(out.toByteArray());if(cropped!=full)cropped.recycle();full.recycle();}catch(Exception e){notice("Capture interrupted; stop and restart sharing if it persists.");}},capture);
  if(display==null)display=projection.createVirtualDisplay("ZDesk",width,height,density,DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,next.getSurface(),null,capture);else{display.resize(width,height,density);display.setSurface(next.getSurface());}if(old!=null)old.close();
 }
 void connect(String code){try{
  String saved=Vault.load(this);enrollment=saved==null?null:new JSONObject(saved);if(code!=null&&!code.isEmpty()||enrollment==null||!url.equals(enrollment.optString("url"))){JSONObject body=new JSONObject().put("code",code).put("name",Build.MANUFACTURER+" "+Build.MODEL+" (Android)");enrollment=new JSONObject(new Api(url,null).json("/api/enroll","POST",body));enrollment.put("url",url);Vault.save(this,enrollment.toString());}
  id=enrollment.getString("id");api=new Api(url,enrollment.getString("token"));loadShares();notice("Screen: "+screen+" · microphone: "+mic+" · selected files: "+files);
  workers.execute(this::commands);if(mic)workers.execute(this::microphone);if(files)workers.execute(this::exchange);
  while(running){try{byte[] jpeg=frame.getAndSet(null);if(!screen)jpeg=statusFrame();if(jpeg!=null){allowControl=screen&&projectionActive&&getSharedPreferences("options",0).getBoolean("control",false)&&ControlService.current!=null;Map<String,String> headers=new HashMap<>();headers.put("Content-Type","image/jpeg");headers.put("X-Allow-Control",allowControl?"yes":"no");headers.put("X-Allow-Audio",mic?"yes":"no");headers.put("X-Allow-Files",files?"yes":"no");headers.put("X-TyDesk-Protocol","2");api.call(base()+"/frame","POST",jpeg,headers);} }catch(Exception e){if(revoked(e))break;notice("Connection interrupted; retrying automatically.");}pause(400);}
 }catch(Exception e){notice("Connection failed. Check your code, server address and network; restart sharing.");main.post(this::stopSelf);}}
 String base(){return "/api/devices/"+id;}
 boolean revoked(Exception e){if(e instanceof Api.Failure&&((Api.Failure)e).code==401){Vault.forget(this);main.post(this::stopSelf);return true;}return false;}
 void commands(){while(running){try{JSONArray commands=new JSONArray(api.json(base()+"/commands","GET",null));for(int i=0;i<commands.length();i++){JSONObject c=commands.getJSONObject(i);main.post(()->{ControlService service=ControlService.current;if(service!=null&&allowControl&&running)service.execute(c);});}}catch(Exception e){if(revoked(e))return;}pause(100);}}
 void microphone(){AudioRecord recorder=null;try{
  if(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)!=android.content.pm.PackageManager.PERMISSION_GRANTED)throw new IOException("Microphone permission is off");
  int rate=24000,size=Math.max(9600,AudioRecord.getMinBufferSize(rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT));
  recorder=new AudioRecord(MediaRecorder.AudioSource.MIC,rate,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size*2);if(recorder.getState()!=AudioRecord.STATE_INITIALIZED)throw new IOException("Microphone is unavailable");recorder.startRecording();final AudioRecord source=recorder;
  Thread sender=new Thread(()->{while(running){byte[] b=audio.getAndSet(null);if(b!=null)try{api.call(base()+"/audio","POST",b,audioHeaders());}catch(Exception e){if(revoked(e))return;notice("Microphone upload delayed; retrying.");}pause(100);}},"ZDesk microphone upload");sender.start();
  short[] mono=new short[4800];while(running){int count=0;while(running&&count<mono.length){int n=source.read(mono,count,mono.length-count);if(n<0)throw new IOException("Microphone capture failed");count+=n;}if(running)audio.set(wav(mono,count));}
 }catch(Exception e){notice("Microphone unavailable. Check Android microphone permission and input.");try{api.json(base()+"/audio-status","POST",new JSONObject().put("state","error").put("message","Android microphone capture unavailable").put("level",0));}catch(Exception ignored){}}
 finally{if(recorder!=null){try{recorder.stop();}catch(Exception ignored){}recorder.release();}}}
 static Map<String,String> audioHeaders(){Map<String,String> h=new HashMap<>();h.put("Content-Type","audio/wav");h.put("X-Audio-Source","microphone");h.put("X-Audio-Level","0");return h;}
 static byte[] wav(short[] samples,int count){ByteBuffer b=ByteBuffer.allocate(44+count*4).order(ByteOrder.LITTLE_ENDIAN);b.put(new byte[]{'R','I','F','F'}).putInt(36+count*4).put(new byte[]{'W','A','V','E','f','m','t',' '}).putInt(16).putShort((short)1).putShort((short)2).putInt(24000).putInt(96000).putShort((short)4).putShort((short)16).put(new byte[]{'d','a','t','a'}).putInt(count*4);for(int i=0;i<count;i++)b.putShort(samples[i]).putShort(samples[i]);return b.array();}
 byte[] statusFrame(){Bitmap bitmap=Bitmap.createBitmap(800,450,Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(bitmap);canvas.drawColor(0xff152237);Paint paint=new Paint();paint.setColor(0xff51e2c0);paint.setTextSize(32);canvas.drawText("ZDesk Android companion",40,150,paint);paint.setTextSize(22);canvas.drawText("Microphone / selected files · screen not shared",40,230,paint);ByteArrayOutputStream out=new ByteArrayOutputStream();bitmap.compress(Bitmap.CompressFormat.JPEG,60,out);bitmap.recycle();return out.toByteArray();}
 void loadShares(){if(!files)return;try{JSONArray uris=new JSONArray(getSharedPreferences("options",0).getString("uris","[]"));for(int i=0;i<uris.length();i++){Uri uri=Uri.parse(uris.getString(i));try(Cursor cursor=getContentResolver().query(uri,null,null,null,null)){if(cursor!=null&&cursor.moveToFirst()){String name=cursor.getString(cursor.getColumnIndexOrThrow(OpenableColumns.DISPLAY_NAME));if(validName(name))shares.put(name,uri);}}}}catch(Exception ignored){}}
 static boolean validName(String name){return name!=null&&name.matches("[A-Za-z0-9][A-Za-z0-9._ -]{0,119}")&&!name.endsWith(".")&&!name.endsWith(" ")&&!name.matches("(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\\..*)?");}
 void exchange(){while(running){try{JSONArray published=new JSONArray();for(Map.Entry<String,Uri> entry:shares.entrySet()){long size=-1;try(Cursor cursor=getContentResolver().query(entry.getValue(),new String[]{OpenableColumns.SIZE},null,null,null)){if(cursor!=null&&cursor.moveToFirst())size=cursor.getLong(0);}if(size>=0&&size<=20*1024*1024)published.put(new JSONObject().put("name",entry.getKey()).put("size",size));}api.json(base()+"/shares","POST",published);JSONArray jobs=new JSONArray(api.json(base()+"/file-jobs","GET",null));for(int i=0;i<jobs.length()&&running;i++){JSONObject job=jobs.getJSONObject(i);String key=job.getString("id"),name=job.getString("name");if(finished.contains(key)||!validName(name)||!key.matches("[a-f0-9]{32}"))continue;
   if(job.getString("direction").equals("from-device")){Uri uri=shares.get(name);if(uri==null)continue;byte[] data;try(InputStream in=getContentResolver().openInputStream(uri)){data=Api.read(in,20*1024*1024);}api.call(base()+"/file-jobs/"+key,"PUT",data,null);}
   else{byte[] data=api.call(base()+"/file-jobs/"+key,"GET",null,null);java.io.File dir=new java.io.File(getExternalFilesDir(null),"Inbox");dir.mkdirs();java.io.File file=new java.io.File(dir,key.substring(0,8)+"-"+name);try(OutputStream out=new FileOutputStream(file)){out.write(data);}api.json(base()+"/file-jobs/"+key+"/ack","POST",new JSONObject().put("success",true));}finished.add(key);
  }}catch(Exception e){if(revoked(e))return;notice("File exchange interrupted; retrying.");}pause(3000);}}
 void pause(long ms){try{Thread.sleep(ms);}catch(InterruptedException e){Thread.currentThread().interrupt();}}
 public void onTimeout(int startId,int type){stopSelf();}
 public void onDestroy(){running=false;active=false;projectionActive=false;allowControl=false;ControlService service=ControlService.current;if(service!=null)service.onInterrupt();if(display!=null)display.release();if(reader!=null)reader.close();if(projection!=null)projection.stop();if(captureThread!=null)captureThread.quitSafely();workers.shutdownNow();if(api!=null&&id!=null)new Thread(()->{try{api.call(base()+"/disconnect","POST",new byte[0],null);}catch(Exception ignored){}},"ZDesk disconnect").start();stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy();}
}
