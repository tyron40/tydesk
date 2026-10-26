package com.zdesk.companion;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.ImageFormat;
import android.hardware.camera2.*;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Size;
import java.nio.ByteBuffer;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicReference;

/** Local consent only; camera ownership and its image queue end with sharing. */
final class CameraFeed implements AutoCloseable {
 final AtomicReference<byte[]> latest=new AtomicReference<>();
 final Context context;final Runnable failed;final HandlerThread thread=new HandlerThread("ZDesk camera");
 Handler handler;CameraDevice device;CameraCaptureSession session;ImageReader reader;
 volatile boolean running=true,ready=false;int orientation;
 CameraFeed(Context context,Runnable failed){this.context=context;this.failed=failed;}
 void start(boolean front,int displayDegrees)throws Exception{
  if(context.checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)throw new SecurityException("Camera permission required");
  CameraManager manager=(CameraManager)context.getSystemService(Context.CAMERA_SERVICE);
  String selected=null;
  for(String id:manager.getCameraIdList()){
   Integer facing=manager.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING);
   if(facing!=null&&facing==(front?CameraCharacteristics.LENS_FACING_FRONT:CameraCharacteristics.LENS_FACING_BACK)){selected=id;break;}
  }
  if(selected==null)throw new IllegalStateException("Selected camera unavailable");
  CameraCharacteristics characteristics=manager.getCameraCharacteristics(selected);
  StreamConfigurationMap map=characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
  if(map==null)throw new IllegalStateException("No camera output");
  Size[] sizes=map.getOutputSizes(ImageFormat.JPEG);if(sizes==null||sizes.length==0)throw new IllegalStateException("No camera JPEG support");
  Size size=sizes[0];long distance=Long.MAX_VALUE;
  for(Size candidate:sizes){long score=Math.abs((long)candidate.getWidth()*candidate.getHeight()-640L*480);if(score<distance){size=candidate;distance=score;}}
  Integer sensor=characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION);
  orientation=((sensor==null?0:sensor)+(front?displayDegrees:-displayDegrees)+360)%360;
  thread.start();handler=new Handler(thread.getLooper());
  reader=ImageReader.newInstance(size.getWidth(),size.getHeight(),ImageFormat.JPEG,2);
  reader.setOnImageAvailableListener(source->{try(Image image=source.acquireLatestImage()){
   if(image==null||!running)return;ByteBuffer buffer=image.getPlanes()[0].getBuffer();if(buffer.remaining()>2*1024*1024)return;
   byte[] jpeg=new byte[buffer.remaining()];buffer.get(jpeg);latest.set(jpeg);
  }catch(Exception e){fail();}},handler);
  manager.openCamera(selected,new CameraDevice.StateCallback(){
   public void onOpened(CameraDevice camera){if(!running){camera.close();return;}device=camera;
    try{camera.createCaptureSession(Collections.singletonList(reader.getSurface()),new CameraCaptureSession.StateCallback(){
     public void onConfigured(CameraCaptureSession configured){if(!running){configured.close();return;}session=configured;ready=true;capture();}
     public void onConfigureFailed(CameraCaptureSession configured){configured.close();fail();}
    },handler);}catch(Exception e){fail();}}
   public void onDisconnected(CameraDevice camera){camera.close();fail();}
   public void onError(CameraDevice camera,int error){camera.close();fail();}
  },handler);
 }
 void capture(){if(!running||device==null||session==null)return;
  try{CaptureRequest.Builder request=device.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);request.addTarget(reader.getSurface());request.set(CaptureRequest.JPEG_QUALITY,(byte)60);request.set(CaptureRequest.JPEG_ORIENTATION,orientation);
   session.capture(request.build(),new CameraCaptureSession.CaptureCallback(){
    public void onCaptureCompleted(CameraCaptureSession s,CaptureRequest r,TotalCaptureResult result){if(running)handler.postDelayed(()->capture(),900);}
    public void onCaptureFailed(CameraCaptureSession s,CaptureRequest r,CaptureFailure failure){fail();}
   },handler);
  }catch(Exception e){fail();}
 }
 synchronized void fail(){if(!running)return;close();failed.run();}
 public synchronized void close(){running=false;ready=false;latest.set(null);if(session!=null){session.close();session=null;}if(device!=null){device.close();device=null;}if(reader!=null){reader.close();reader=null;}if(handler!=null)handler.removeCallbacksAndMessages(null);thread.quitSafely();}
}
