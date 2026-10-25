package com.zdesk.companion;
import android.accessibilityservice.*;
import android.view.accessibility.*;
import android.graphics.Path;
import android.os.Bundle;
import org.json.*;
public class ControlService extends AccessibilityService {
 static volatile ControlService current;
 long lastInput=0;Path drag;float x=.5f,y=.5f;boolean ctrl=false;
 protected void onServiceConnected(){current=this;}
 public void onAccessibilityEvent(AccessibilityEvent e){}
 public void onInterrupt(){drag=null;ctrl=false;}
 public void onDestroy(){current=null;super.onDestroy();}
 void gesture(Path path,long duration){dispatchGesture(new GestureDescription.Builder().addStroke(new GestureDescription.StrokeDescription(path,0,Math.max(1,duration))).build(),null,null);}
 float px(float x){return x*Math.max(1,ShareService.deviceWidth-1);}float py(float y){return y*Math.max(1,ShareService.deviceHeight-1);}
 void execute(JSONObject c){
  if(!ShareService.active||!ShareService.projectionActive||!ShareService.allowControl)return;
  long now=android.os.SystemClock.elapsedRealtime();if(now-lastInput>1500){drag=null;ctrl=false;}lastInput=now;
  String type=c.optString("type"),key=c.optString("key");
  if(type.equals("release")){drag=null;ctrl=false;return;}
  if(type.equals("hold"))return;
  if(type.equals("click")||type.equals("move")||type.equals("pointer_down")||type.equals("pointer_up")){
   x=Math.max(0,Math.min(1,(float)c.optDouble("x",.5)));y=Math.max(0,Math.min(1,(float)c.optDouble("y",.5)));
   if(type.equals("pointer_down")){drag=new Path();drag.moveTo(px(x),py(y));}
   else if(type.equals("move")){if(drag!=null)drag.lineTo(px(x),py(y));}
   else if(type.equals("pointer_up")){if(drag!=null){drag.lineTo(px(x),py(y));gesture(drag,280);drag=null;}}
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
