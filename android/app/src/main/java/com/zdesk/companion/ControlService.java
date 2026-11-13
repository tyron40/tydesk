package com.zdesk.companion;
import android.accessibilityservice.*;
import android.view.accessibility.*;
import android.graphics.Path;
import android.os.Bundle;
import org.json.*;
public class ControlService extends AccessibilityService {
 static volatile ControlService current;
 long lastInput=0;Path drag;float x=.5f,y=.5f;boolean ctrl=false;GestureDescription.StrokeDescription liveStroke;boolean gestureBusy=false;float queuedX,queuedY;boolean queuedMove=false,finishDrag=false;
 protected void onServiceConnected(){current=this;}
 public void onAccessibilityEvent(AccessibilityEvent e){}
 public void onInterrupt(){resetDrag();ctrl=false;}
 public void onDestroy(){current=null;super.onDestroy();}
 void resetDrag(){drag=null;liveStroke=null;gestureBusy=false;queuedMove=false;finishDrag=false;}
 void gesture(Path path,long duration){dispatchGesture(new GestureDescription.Builder().addStroke(new GestureDescription.StrokeDescription(path,0,Math.max(1,duration))).build(),null,null);}
 void dispatchLive(GestureDescription.StrokeDescription stroke){gestureBusy=true;boolean started=dispatchGesture(new GestureDescription.Builder().addStroke(stroke).build(),new GestureResultCallback(){@Override public void onCompleted(GestureDescription g){gestureBusy=false;if(queuedMove){float nx=queuedX,ny=queuedY;boolean end=finishDrag;queuedMove=false;continueDrag(nx,ny,end);}else if(finishDrag)resetDrag();}@Override public void onCancelled(GestureDescription g){resetDrag();}},null);if(!started)resetDrag();}
 void continueDrag(float nx,float ny,boolean end){if(liveStroke==null)return;if(gestureBusy){queuedX=nx;queuedY=ny;queuedMove=true;finishDrag|=end;return;}Path segment=new Path();segment.moveTo(px(x),py(y));segment.lineTo(px(nx),py(ny));x=nx;y=ny;try{liveStroke=liveStroke.continueStroke(segment,0,end?55:95,!end);dispatchLive(liveStroke);}catch(Exception ex){resetDrag();}}
 float px(float x){return x*Math.max(1,ShareService.deviceWidth-1);}float py(float y){return y*Math.max(1,ShareService.deviceHeight-1);}
 void execute(JSONObject c){
  if(!ShareService.active||!ShareService.projectionActive||!ShareService.allowControl)return;
  long now=android.os.SystemClock.elapsedRealtime();if(now-lastInput>1500){resetDrag();ctrl=false;}lastInput=now;
  String type=c.optString("type"),key=c.optString("key");
  if(type.equals("release")){if(liveStroke!=null){finishDrag=true;continueDrag(x,y,true);}else resetDrag();ctrl=false;return;}
  if(type.equals("hold"))return;
  if(type.equals("click")||type.equals("move")||type.equals("pointer_down")||type.equals("pointer_up")){
   x=Math.max(0,Math.min(1,(float)c.optDouble("x",.5)));y=Math.max(0,Math.min(1,(float)c.optDouble("y",.5)));
   if(type.equals("pointer_down")){resetDrag();drag=new Path();drag.moveTo(px(x),py(y));if(android.os.Build.VERSION.SDK_INT>=26){liveStroke=new GestureDescription.StrokeDescription(drag,0,250,true);dispatchLive(liveStroke);}}
   else if(type.equals("move")){if(drag!=null){if(android.os.Build.VERSION.SDK_INT>=26){continueDrag(x,y,false);}else drag.lineTo(px(x),py(y));}}
   else if(type.equals("pointer_up")){if(drag!=null){if(android.os.Build.VERSION.SDK_INT>=26){finishDrag=true;continueDrag(x,y,true);}else{drag.lineTo(px(x),py(y));gesture(drag,Math.min(450,Math.max(100,now-lastInput+150)));resetDrag();}}}
   else{Path p=new Path();p.moveTo(px(x),py(y));gesture(p,c.optString("button").equals("right")?650:60);}
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
