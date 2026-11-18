package com.zdesk.companion;
import android.accessibilityservice.*;
import android.view.accessibility.*;
import android.graphics.Path;
import android.os.Bundle;
import org.json.*;
public class ControlService extends AccessibilityService {
 static volatile ControlService current;
 long lastInput=0;float x=.5f,y=.5f;boolean ctrl=false;
 final android.os.Handler main=new android.os.Handler(android.os.Looper.getMainLooper());
 final Runnable idleRelease=this::releaseTouch;
 GestureDescription.StrokeDescription liveStroke;
 float strokeX,strokeY,nextX,nextY;
 int generation,strokeWidth,strokeHeight;
 boolean gestureBusy,pending,ending;
 protected void onServiceConnected(){current=this;}
 public void onAccessibilityEvent(AccessibilityEvent e){}
 public void onInterrupt(){releaseTouch();ctrl=false;}
 public void onDestroy(){releaseTouch();current=null;super.onDestroy();}
 boolean allowed(){return ShareService.active&&ShareService.projectionActive&&ShareService.allowControl;}
 void resetTouch(){generation++;main.removeCallbacks(idleRelease);liveStroke=null;gestureBusy=false;pending=false;ending=false;}
 void gesture(Path path,long duration){resetTouch();dispatchGesture(new GestureDescription.Builder().addStroke(new GestureDescription.StrokeDescription(path,0,Math.max(1,duration))).build(),null,null);}
 void armRelease(){main.removeCallbacks(idleRelease);main.postDelayed(idleRelease,850);}
 void releaseTouch(){
  if(liveStroke==null)return;
  ending=true;pending=true;nextX=strokeX;nextY=strokeY;
  flushTouch();
 }
 void dispatchLive(GestureDescription.StrokeDescription stroke,boolean finalSegment){
  gestureBusy=true;int ticket=generation;
  boolean sent=dispatchGesture(new GestureDescription.Builder().addStroke(stroke).build(),new GestureResultCallback(){
   @Override public void onCompleted(GestureDescription g){
    if(ticket!=generation)return;
    gestureBusy=false;
    if(finalSegment){resetTouch();return;}
    if(!allowed()||strokeWidth!=ShareService.deviceWidth||strokeHeight!=ShareService.deviceHeight)releaseTouch();
    else flushTouch();
   }
   @Override public void onCancelled(GestureDescription g){if(ticket==generation)resetTouch();}
  },main);
  if(!sent)resetTouch();
 }
 void beginTouch(float nx,float ny){
  resetTouch();strokeWidth=ShareService.deviceWidth;strokeHeight=ShareService.deviceHeight;
  strokeX=px(nx);strokeY=py(ny);
  Path start=new Path();start.moveTo(strokeX,strokeY);
  liveStroke=new GestureDescription.StrokeDescription(start,0,16,true);
  armRelease();dispatchLive(liveStroke,false);
 }
 void queueTouch(float nx,float ny,boolean end){
  if(liveStroke==null||ending)return;
  if(strokeWidth!=ShareService.deviceWidth||strokeHeight!=ShareService.deviceHeight){releaseTouch();return;}
  nextX=px(nx);nextY=py(ny);pending=true;ending=end;
  if(!end)armRelease();else main.removeCallbacks(idleRelease);
  flushTouch();
 }
 void flushTouch(){
  if(liveStroke==null||gestureBusy||!pending)return;
  if(!allowed()){ending=true;nextX=strokeX;nextY=strokeY;}
  boolean end=ending;pending=false;
  Path segment=new Path();segment.moveTo(strokeX,strokeY);
  if(nextX!=strokeX||nextY!=strokeY)segment.lineTo(nextX,nextY);
  try{
   liveStroke=liveStroke.continueStroke(segment,0,end?16:32,!end);
   strokeX=nextX;strokeY=nextY;dispatchLive(liveStroke,end);
  }catch(IllegalArgumentException|IllegalStateException ex){resetTouch();}
 }
 float px(float x){return x*Math.max(1,ShareService.deviceWidth-1);}float py(float y){return y*Math.max(1,ShareService.deviceHeight-1);}
 void execute(JSONObject c){
  if(!allowed()){releaseTouch();return;}
  long now=android.os.SystemClock.elapsedRealtime();if(now-lastInput>1500)ctrl=false;lastInput=now;
  String type=c.optString("type"),key=c.optString("key");
  if(type.equals("release")){releaseTouch();ctrl=false;return;}
  if(type.equals("hold")){if(liveStroke!=null&&!ending)armRelease();return;}
  if(type.equals("click")||type.equals("move")||type.equals("pointer_down")||type.equals("pointer_up")){
   x=Math.max(0,Math.min(1,(float)c.optDouble("x",.5)));y=Math.max(0,Math.min(1,(float)c.optDouble("y",.5)));
   if(type.equals("pointer_down"))beginTouch(x,y);
   else if(type.equals("move"))queueTouch(x,y,false);
   else if(type.equals("pointer_up"))queueTouch(x,y,true);
   else{Path p=new Path();p.moveTo(px(x),py(y));gesture(p,c.optString("button").equals("right")?650:35);}
   return;
  }
  if(type.equals("scroll")){Path p=new Path();p.moveTo(px(.5f),py(.5f));p.lineTo(px(.5f),py(c.optDouble("amount")>0?.8f:.2f));gesture(p,220);return;}
  if(type.equals("key_down")){if(key.equals("ctrl"))ctrl=true;return;}if(type.equals("key_up")){if(key.equals("ctrl"))ctrl=false;return;}
  if(type.equals("key")&&key.equals("esc")){performGlobalAction(GLOBAL_ACTION_BACK);return;}if(type.equals("key")&&key.equals("home")){performGlobalAction(GLOBAL_ACTION_HOME);return;}
  AccessibilityNodeInfo root=getRootInActiveWindow();if(root==null)return;AccessibilityNodeInfo node=root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);if(node==null)return;
  if(ctrl&&type.equals("key")){int action=key.equals("c")?AccessibilityNodeInfo.ACTION_COPY:key.equals("v")?AccessibilityNodeInfo.ACTION_PASTE:0;if(action!=0)node.performAction(action);return;}
  if(node.isPassword())return;
  String text=node.getText()==null?"":node.getText().toString();
  if(type.equals("text"))text+=c.optString("text");else if(type.equals("key")&&key.equals("backspace"))text=text.isEmpty()?text:text.substring(0,text.length()-1);else if(type.equals("key")&&key.equals("space"))text+=" ";else if(type.equals("key")&&key.length()==1)text+=key;else if(type.equals("key")&&key.equals("enter")&&android.os.Build.VERSION.SDK_INT>=30){node.performAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_IME_ENTER.getId());return;}else return;
  Bundle args=new Bundle();args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,text);node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,args);
 }
}
