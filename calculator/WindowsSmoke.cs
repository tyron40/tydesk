using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Threading;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Windows.Forms;
using System.Runtime.InteropServices;
class WindowsSmoke {
 delegate bool Callback(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h,Callback c,IntPtr p);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h,int m,IntPtr w,IntPtr l);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr h,int m,IntPtr w,StringBuilder l);
 [DllImport("user32.dll",SetLastError=true)] static extern IntPtr SendMessageTimeout(IntPtr h,uint m,IntPtr w,IntPtr l,uint flags,uint timeout,out IntPtr result);
 [DllImport("user32.dll",SetLastError=true)] static extern bool PostMessage(IntPtr h,uint message,IntPtr w,IntPtr l);
 static string Text(IntPtr h){var s=new StringBuilder(1024);SendMessage(h,0xD,new IntPtr(s.Capacity),s);return s.ToString();}
 static string Class(IntPtr h){var s=new StringBuilder(256);GetClassName(h,s,s.Capacity);return s.ToString();}
 static void Wait(Func<bool> condition,string why,int seconds=20){var watch=Stopwatch.StartNew();while(!condition()){if(watch.Elapsed.TotalSeconds>seconds)throw new Exception(why);Application.DoEvents();Thread.Sleep(80);}Application.DoEvents();}
 static List<IntPtr> Children(IntPtr h){var children=new List<IntPtr>();EnumChildWindows(h,delegate(IntPtr x,IntPtr p){if(IsWindowVisible(x))children.Add(x);return true;},IntPtr.Zero);return children;}
 static void Click(IntPtr h,string text){foreach(var c in Children(h))if(Class(c).IndexOf("button",StringComparison.OrdinalIgnoreCase)>=0&&Text(c)==text){if(!PostMessage(c,0xF5,IntPtr.Zero,IntPtr.Zero))throw new Exception("Could not post button click: "+text);for(int i=0;i<5;i++){Application.DoEvents();Thread.Sleep(30);}return;}foreach(var child in Children(h))Console.WriteLine("Visible control: "+Class(child)+" / "+Text(child));throw new Exception("Missing visible button: "+text);}
 static string Display(IntPtr h){foreach(var c in Children(h))if(Class(c).IndexOf("edit",StringComparison.OrdinalIgnoreCase)>=0){var s=new StringBuilder(1024);SendMessage(c,0xD,new IntPtr(s.Capacity),s);return s.ToString();}throw new Exception("No calculator display");}
 static bool HasLabel(IntPtr h,string text){foreach(var c in Children(h))if(Text(c)==text)return true;return false;}
 static void SelectTarget(IntPtr h,string title){foreach(var c in Children(h)){if(Class(c).IndexOf("listbox",StringComparison.OrdinalIgnoreCase)<0)continue;int count=SendMessage(c,0x18B,IntPtr.Zero,IntPtr.Zero).ToInt32();for(int i=0;i<count;i++){var s=new StringBuilder(2048);SendMessage(c,0x189,new IntPtr(i),s);if(s.ToString().Contains(title)){SendMessage(c,0x186,new IntPtr(i),IntPtr.Zero);return;}}}throw new Exception("Test target window is missing from window list");}
 [STAThread] static int Main(string[] args){
  Process app=null;Form target=null;
  try{
   string source=Path.GetFullPath(args[0]);string configured=Path.Combine(Path.GetDirectoryName(source),"Configured Calculator Test.exe");
   byte[] binary=File.ReadAllBytes(source),salt=new byte[16];for(int i=0;i<16;i++)salt[i]=(byte)i;
   byte[] hash;using(var k=new Rfc2898DeriveBytes("072839",salt,210000,HashAlgorithmName.SHA256))hash=k.GetBytes(32);
   using(var output=File.Create(configured)){output.Write(binary,0,binary.Length);output.Write(salt,0,salt.Length);output.Write(hash,0,hash.Length);byte[] marker=Encoding.ASCII.GetBytes("ZDESKCALCPIN0002");output.Write(marker,0,marker.Length);}
   Application.EnableVisualStyles();target=new Form{Text="Calculator Windows smoke target",Width=360,Height=200};target.Show();Application.DoEvents();
   app=Process.Start(new ProcessStartInfo(configured){UseShellExecute=false});IntPtr window=IntPtr.Zero;
   Wait(delegate{app.Refresh();if(app.HasExited)throw new Exception("Calculator exited before showing UI: "+app.ExitCode);window=app.MainWindowHandle;return window!=IntPtr.Zero&&IsWindowVisible(window);},"Calculator never showed a window",45);
   if(Text(window)!="System Calculator")throw new Exception("Unexpected startup window: "+Text(window));
   if(!HasLabel(window,"Standard")||HasLabel(window,"Private window panel"))throw new Exception("Startup is not a plain calculator");
   Console.WriteLine("CHECK: arithmetic");Click(window,"2");Click(window,"+");Click(window,"2");Click(window,"=");if(Display(window)!="4")throw new Exception("2+2 did not produce 4: "+Display(window));
   Console.WriteLine("CHECK: configured password");Click(window,"C");foreach(char c in "072839")Click(window,c.ToString());Click(window,"=");
   Wait(()=>HasLabel(window,"Private window panel"),"PIN from appended download configuration did not unlock the panel");
   Console.WriteLine("CHECK: hide and restore");SelectTarget(window,target.Text);Click(window,"Hide selected");Wait(()=>!IsWindowVisible(target.Handle),"Hide selected did not hide the test window");
   Click(window,"Restore all");Wait(()=>IsWindowVisible(target.Handle),"Restore all did not restore the test window");
   Click(window,"Lock");if(!HasLabel(window,"Standard"))throw new Exception("Lock did not restore calculator view");
   Click(window,"C");foreach(char c in "072839")Click(window,c.ToString());Click(window,"=");SelectTarget(window,target.Text);Click(window,"Hide selected");Wait(()=>!IsWindowVisible(target.Handle),"Second hide failed");
   Console.WriteLine("CHECK: crash recovery");app.Kill();app.WaitForExit();Wait(()=>IsWindowVisible(target.Handle),"Recovery monitor did not restore the test window after process termination",20);
   File.WriteAllText("calculator-windows-smoke.json","{\"ok\":true,\"startup\":true,\"arithmetic\":true,\"download_pin\":true,\"hide_restore\":true,\"lock\":true,\"crash_recovery\":true}");
   Console.WriteLine("PASS: visible calculator startup, 2+2=4, configured PIN, hide/restore, lock and crash recovery.");return 0;
  }catch(Exception e){Console.Error.WriteLine(e);try{string log=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CalculatorVault","startup-error.log");if(File.Exists(log)){File.Copy(log,"calculator-startup-error.log",true);Console.Error.WriteLine(File.ReadAllText(log));}}catch{}return 1;}
  finally{if(app!=null&&!app.HasExited){app.Kill();app.WaitForExit();}if(target!=null){target.Show();target.Close();}}
 }
}
