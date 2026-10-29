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
 [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr h);
 [DllImport("user32.dll")] static extern int GetDlgCtrlID(IntPtr h);
 static string Text(IntPtr h){var s=new StringBuilder(1024);SendMessage(h,0xD,new IntPtr(s.Capacity),s);return s.ToString();}
 static string Class(IntPtr h){var s=new StringBuilder(256);GetClassName(h,s,s.Capacity);return s.ToString();}
 static void Wait(Func<bool> condition,string why,int seconds=20){var watch=Stopwatch.StartNew();while(!condition()){if(watch.Elapsed.TotalSeconds>seconds)throw new Exception(why);Application.DoEvents();Thread.Sleep(80);}Application.DoEvents();}
 static List<IntPtr> Children(IntPtr h){var children=new List<IntPtr>();EnumChildWindows(h,delegate(IntPtr x,IntPtr p){if(IsWindowVisible(x))children.Add(x);return true;},IntPtr.Zero);return children;}
 static void Click(IntPtr h,string text){foreach(var c in Children(h))if(Class(c).IndexOf("button",StringComparison.OrdinalIgnoreCase)>=0&&Text(c)==text){if(!PostMessage(c,0xF5,IntPtr.Zero,IntPtr.Zero))throw new Exception("Could not post button click: "+text);for(int i=0;i<5;i++){Application.DoEvents();Thread.Sleep(30);}return;}foreach(var child in Children(h))Console.WriteLine("Visible control: "+Class(child)+" / "+Text(child));throw new Exception("Missing visible button: "+text);}
 static string Display(IntPtr h){foreach(var c in Children(h))if(Class(c).IndexOf("edit",StringComparison.OrdinalIgnoreCase)>=0){var s=new StringBuilder(1024);SendMessage(c,0xD,new IntPtr(s.Capacity),s);return s.ToString();}throw new Exception("No calculator display");}
 static bool HasLabel(IntPtr h,string text){foreach(var c in Children(h))if(Text(c)==text)return true;return false;}
 static void SelectTarget(IntPtr h,string title){foreach(var c in Children(h)){if(Class(c).IndexOf("listbox",StringComparison.OrdinalIgnoreCase)<0)continue;int count=SendMessage(c,0x18B,IntPtr.Zero,IntPtr.Zero).ToInt32();for(int i=0;i<count;i++){var s=new StringBuilder(2048);SendMessage(c,0x189,new IntPtr(i),s);if(s.ToString().Contains(title)){SendMessage(c,0x186,new IntPtr(i),IntPtr.Zero);SendMessage(GetParent(c),0x111,new IntPtr((GetDlgCtrlID(c)&0xffff)|(1<<16)),c);Application.DoEvents();return;}}}throw new Exception("Test target window is missing from window list");}
 static void SelectQuickTarget(IntPtr h,string title){foreach(var c in Children(h)){if(Class(c).IndexOf("combobox",StringComparison.OrdinalIgnoreCase)<0)continue;int count=SendMessage(c,0x146,IntPtr.Zero,IntPtr.Zero).ToInt32();for(int i=0;i<count;i++){var text=new StringBuilder(2048);SendMessage(c,0x148,new IntPtr(i),text);if(text.ToString().Contains(title)){SendMessage(c,0x14E,new IntPtr(i),IntPtr.Zero);SendMessage(GetParent(c),0x111,new IntPtr((GetDlgCtrlID(c)&0xffff)|(1<<16)),c);Application.DoEvents();return;}}}throw new Exception("Window not found in persistent selector: "+title);}
 static void RequireQuickControls(IntPtr h){foreach(string text in new[]{"Hide window","Restore window","Restore all windows","Refresh windows","Lock"})if(!HasLabel(h,text))throw new Exception("Persistent control disappeared: "+text);}
 static void SetEdit(IntPtr h,string value){foreach(var c in Children(h))if(Class(c).IndexOf("edit",StringComparison.OrdinalIgnoreCase)>=0){SendMessageText(c,0xC,IntPtr.Zero,value);return;}throw new Exception("Missing input");}
 [DllImport("user32.dll",EntryPoint="SendMessageW",CharSet=CharSet.Unicode)] static extern IntPtr SendMessageText(IntPtr h,int m,IntPtr w,string text);
 static void SelectFirstRow(IntPtr h){foreach(var c in Children(h))if(Class(c).IndexOf("SysListView32",StringComparison.OrdinalIgnoreCase)>=0){PostMessage(c,0x201,new IntPtr(1),new IntPtr((35<<16)|25));PostMessage(c,0x202,IntPtr.Zero,new IntPtr((35<<16)|25));for(int i=0;i<5;i++){Application.DoEvents();Thread.Sleep(50);}return;}throw new Exception("Missing browser list");}
 [DllImport("user32.dll")] static extern bool EnumWindows(Callback callback,IntPtr unused);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 static void DismissVaultError(int pid){IntPtr dialog=IntPtr.Zero;Wait(delegate{EnumWindows(delegate(IntPtr h,IntPtr unused){uint id;GetWindowThreadProcessId(h,out id);if(id==pid&&Text(h)=="Some items could not be changed"){dialog=h;return false;}return true;},IntPtr.Zero);return dialog!=IntPtr.Zero;},"Expected restore conflict message");Click(dialog,"OK");}
 static string StoredPath(string data,string original){foreach(string line in File.ReadAllLines(Path.Combine(data,"vault-items-v2.txt"))){string[] a=line.Split('|');if(a.Length==7&&Encoding.UTF8.GetString(Convert.FromBase64String(a[1]))==original)return Encoding.UTF8.GetString(Convert.FromBase64String(a[2]));}throw new Exception("Recovery journal missing: "+original);}
 static void MakeShortcut(string link,string target){string script="$shell=New-Object -ComObject WScript.Shell; $link=$shell.CreateShortcut('"+link.Replace("'","''")+"'); $link.TargetPath='"+target.Replace("'","''")+"'; $link.Save()";var child=Process.Start(new ProcessStartInfo("powershell.exe","-NoProfile -NonInteractive -EncodedCommand "+Convert.ToBase64String(Encoding.Unicode.GetBytes(script))){UseShellExecute=false,CreateNoWindow=true});Wait(()=>child.HasExited,"Shortcut creation timed out",20);if(child.ExitCode!=0||!File.Exists(link))throw new Exception("Could not create shortcut fixture");}
 [STAThread] static int Main(string[] args){
  if(Path.GetFileName(Application.ExecutablePath)=="Calculator Smoke Fixture.exe"){File.WriteAllText(Path.Combine(Path.GetTempPath(),"CalculatorAppLaunched.txt"),"launched");return 0;}
  string fixture=null,shortcutFixture=null,testDataDir=null,legacyFixture=null;
  Process app=null;Form target=null;
  try{
   string source=Path.GetFullPath(args[0]);string configured=Path.Combine(Path.GetDirectoryName(source),"Configured Calculator Test.exe");
   bool launchOnly=args.Length>1&&args[1]=="--launch-only";
   byte[] binary=File.ReadAllBytes(source),salt=new byte[16];for(int i=0;i<16;i++)salt[i]=(byte)i;
   byte[] hash;using(var k=new Rfc2898DeriveBytes("072839",salt,210000,HashAlgorithmName.SHA256))hash=k.GetBytes(32);
   if(!launchOnly)using(var output=File.Create(configured)){output.Write(binary,0,binary.Length);output.Write(salt,0,salt.Length);output.Write(hash,0,hash.Length);byte[] marker=Encoding.ASCII.GetBytes("ZDESKCALCPIN0002");output.Write(marker,0,marker.Length);}
   if(!launchOnly){testDataDir=Path.Combine(Path.GetTempPath(),"CalculatorData-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(testDataDir);Environment.SetEnvironmentVariable("ZDESK_CALCULATOR_DATA_DIR",testDataDir);legacyFixture=Path.Combine(Path.GetTempPath(),"CalculatorLegacy-"+Guid.NewGuid().ToString("N")+".txt");File.WriteAllText(legacyFixture,"legacy");File.SetAttributes(legacyFixture,FileAttributes.Hidden|FileAttributes.ReadOnly);File.WriteAllText(Path.Combine(testDataDir,"hidden-files-v1.txt"),Convert.ToBase64String(Encoding.UTF8.GetBytes(legacyFixture))+Environment.NewLine);}
   Application.EnableVisualStyles();target=new Form{Text="Calculator Windows smoke target",Width=360,Height=200};target.Show();Application.DoEvents();
   app=Process.Start(new ProcessStartInfo(launchOnly?source:configured){UseShellExecute=launchOnly});IntPtr window=IntPtr.Zero;
   Wait(delegate{app.Refresh();if(app.HasExited)throw new Exception("Calculator exited before showing UI: "+app.ExitCode);window=app.MainWindowHandle;return window!=IntPtr.Zero&&IsWindowVisible(window);},"Calculator never showed a window",45);
   if(Text(window)!="System Calculator")throw new Exception("Unexpected startup window: "+Text(window));
   if(!HasLabel(window,"Scientific")||HasLabel(window,"Private window panel"))throw new Exception("Startup is not a plain calculator");
   Console.WriteLine("CHECK: arithmetic");Click(window,"2");Click(window,"+");Click(window,"2");Click(window,"=");if(Display(window)!="4")throw new Exception("2+2 did not produce 4: "+Display(window));
   if(launchOnly){app.CloseMainWindow();app.WaitForExit(5000);Console.WriteLine("PASS: exact website-downloaded executable opened a desktop calculator and calculated 2+2=4.");return 0;}
   Console.WriteLine("CHECK: scientific functions");
   Click(window,"C");Click(window,"9");Click(window,"sqrt");if(Display(window)!="3")throw new Exception("Square root failed");
   Click(window,"C");Click(window,"3");Click(window,"0");Click(window,"sin");if(Math.Abs(double.Parse(Display(window),System.Globalization.CultureInfo.InvariantCulture)-0.5)>1e-10)throw new Exception("Degree sine failed");
   Click(window,"C");Click(window,"2");Click(window,"x^y");Click(window,"3");Click(window,"=");if(Display(window)!="8")throw new Exception("Power failed");
   Click(window,"C");Click(window,"(");Click(window,"2");Click(window,"+");Click(window,"3");Click(window,")");Click(window,"*");Click(window,"4");Click(window,"=");if(Display(window)!="20")throw new Exception("Parentheses failed");
   Console.WriteLine("CHECK: password immediately after calculation, without clearing");foreach(char c in "072839")Click(window,c.ToString());Click(window,"=");
   Wait(()=>HasLabel(window,"Private window panel"),"PIN from appended download configuration did not unlock the panel");
   Console.WriteLine("CHECK: migrate old attribute-only hidden items into storage and restore");
   Click(window,"Hidden files/apps");Wait(()=>HasLabel(window,"1 hidden items"),"Legacy item was not imported");SelectFirstRow(window);Click(window,"Move old hidden items");Wait(()=>!File.Exists(legacyFixture),"Legacy hidden item was not removed from original location");if(File.ReadAllText(StoredPath(testDataDir,legacyFixture))!="legacy")throw new Exception("Legacy content changed in storage");
   SelectFirstRow(window);Click(window,"Restore selected");Wait(()=>File.Exists(legacyFixture),"Legacy item did not restore");if((File.GetAttributes(legacyFixture)&FileAttributes.Hidden)!=0||(File.GetAttributes(legacyFixture)&FileAttributes.ReadOnly)==0)throw new Exception("Legacy attributes were not correctly restored");
   File.SetAttributes(legacyFixture,FileAttributes.Normal);File.Delete(legacyFixture);
   Console.WriteLine("CHECK: file navigation and app catalog");
   string browserRoot=Path.Combine(Path.GetTempPath(),"CalculatorBrowserFixture-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(Path.Combine(browserRoot,"Child"));File.WriteAllText(Path.Combine(browserRoot,"Sample.txt"),"test");
   Click(window,"Files");Wait(()=>HasLabel(window,"Your files"),"Files page missing");SetEdit(window,browserRoot);Click(window,"Go");Wait(()=>HasLabel(window,"1 folders · 1 files"),"File browser did not enumerate fixture");
   SelectFirstRow(window);Click(window,"Open selected");Wait(()=>HasLabel(window,"0 folders · 0 files"),"Folder navigation failed");Click(window,"Up");Wait(()=>HasLabel(window,"1 folders · 1 files"),"Parent navigation failed");
   Console.WriteLine("CHECK: hide folder removes original location and preserves nested contents");
   string testFolder=Path.Combine(browserRoot,"Child"),testFile=Path.Combine(browserRoot,"Sample.txt");File.WriteAllText(Path.Combine(testFolder,"Nested.txt"),"nested content");
   SelectFirstRow(window);Click(window,"Hide selected");Wait(()=>!Directory.Exists(testFolder),"Hidden folder remained at its original location");if(File.ReadAllText(Path.Combine(StoredPath(testDataDir,testFolder),"Nested.txt"))!="nested content")throw new Exception("Folder content changed in storage");
   Click(window,"Hidden files/apps");Wait(()=>HasLabel(window,"1 hidden items"),"Hidden folder missing from recovery list");SelectFirstRow(window);Click(window,"Restore selected");Wait(()=>Directory.Exists(testFolder),"Selected folder did not restore");if(File.ReadAllText(Path.Combine(testFolder,"Nested.txt"))!="nested content")throw new Exception("Restored folder content changed");Click(window,"Back to files");
   Console.WriteLine("CHECK: moved files/folders survive restart and restore all without changing contents or read-only attribute");
   File.SetAttributes(testFile,File.GetAttributes(testFile)|FileAttributes.ReadOnly);
   SelectFirstRow(window);Click(window,"Hide selected");Wait(()=>!Directory.Exists(testFolder),"Second folder move failed");
   SelectFirstRow(window);Click(window,"Hide selected");Wait(()=>!File.Exists(testFile),"Selected file remained at original location");if(File.ReadAllText(StoredPath(testDataDir,testFile))!="test")throw new Exception("Moved file content changed");
   app.CloseMainWindow();Wait(()=>app.HasExited,"Calculator did not exit for vault persistence test");
   app=Process.Start(new ProcessStartInfo(configured){UseShellExecute=false});window=IntPtr.Zero;
   Wait(delegate{app.Refresh();if(app.HasExited)throw new Exception("Restarted calculator exited");window=app.MainWindowHandle;return window!=IntPtr.Zero&&IsWindowVisible(window);},"Calculator restart did not show UI",45);
   foreach(char c in "072839")Click(window,c.ToString());Click(window,"=");Click(window,"Hidden files/apps");Wait(()=>HasLabel(window,"2 hidden items"),"Moved item records did not survive restart");
   if(File.Exists(testFile)||Directory.Exists(testFolder))throw new Exception("Hidden originals reappeared after restart");
   Console.WriteLine("CHECK: restore refuses to overwrite an occupied original location");
   Directory.CreateDirectory(testFolder);File.WriteAllText(Path.Combine(testFolder,"Collision.txt"),"keep me");SelectFirstRow(window);Click(window,"Restore selected");DismissVaultError(app.Id);
   if(File.ReadAllText(Path.Combine(testFolder,"Collision.txt"))!="keep me"||!Directory.Exists(StoredPath(testDataDir,testFolder)))throw new Exception("Restore conflict overwrote or lost data");
   Directory.Delete(testFolder,true);Click(window,"Restore all items");Wait(()=>File.Exists(testFile)&&Directory.Exists(testFolder),"Restore all did not restore file and folder");
   if((File.GetAttributes(testFile)&FileAttributes.ReadOnly)==0||File.ReadAllText(testFile)!="test"||File.ReadAllText(Path.Combine(testFolder,"Nested.txt"))!="nested content")throw new Exception("Restore changed contents or attributes");
   File.SetAttributes(testFile,File.GetAttributes(testFile)&~FileAttributes.ReadOnly);Click(window,"Back to files");SetEdit(window,browserRoot);Click(window,"Go");Wait(()=>HasLabel(window,"1 folders · 1 files"),"Restored items did not return to file browser");
   if(!Path.GetPathRoot(source).Equals(Path.GetPathRoot(testDataDir),StringComparison.OrdinalIgnoreCase)){
    Console.WriteLine("CHECK: hiding from another drive uses storage on that same drive");
    string otherFolder=Path.Combine(Path.GetDirectoryName(source),"OtherDriveFixture-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(otherFolder);string otherFile=Path.Combine(otherFolder,"Second.txt");File.WriteAllText(otherFile,"second drive");
    SetEdit(window,otherFolder);Click(window,"Go");SelectFirstRow(window);Click(window,"Hide selected");Wait(()=>!File.Exists(otherFile),"Other-drive source remained visible");
    string stored=StoredPath(testDataDir,otherFile);if(!Path.GetPathRoot(stored).Equals(Path.GetPathRoot(otherFile),StringComparison.OrdinalIgnoreCase)||File.ReadAllText(stored)!="second drive")throw new Exception("Other-drive storage did not preserve volume and contents");
    Click(window,"Hidden files/apps");SelectFirstRow(window);Click(window,"Restore selected");Wait(()=>File.Exists(otherFile),"Other-drive restore failed");Click(window,"Back to files");SetEdit(window,browserRoot);Click(window,"Go");
   }
   Console.WriteLine("CHECK: persistent window actions while browsing files and folders");
   RequireQuickControls(window);Click(window,"Refresh windows");SelectQuickTarget(window,target.Text);Click(window,"Hide window");Wait(()=>!IsWindowVisible(target.Handle),"Persistent hide failed on Files page");if(!HasLabel(window,"Your files"))throw new Exception("Hide action navigated away from Files");
   SelectQuickTarget(window,target.Text);Click(window,"Restore window");Wait(()=>IsWindowVisible(target.Handle),"Persistent restore failed on Files page");

   fixture=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),"Calculator Smoke Fixture.exe");File.Copy(Application.ExecutablePath,fixture,true);
   Click(window,"Apps");Wait(()=>HasLabel(window,"Your apps"),"Apps page missing");SetEdit(window,"Calculator Smoke Fixture");Wait(()=>HasLabel(window,"1 apps · All Windows apps includes registered Store apps."),"App search did not find fixture");
   string launched=Path.Combine(Path.GetTempPath(),"CalculatorAppLaunched.txt");if(File.Exists(launched))File.Delete(launched);
   SelectFirstRow(window);Click(window,"Launch selected");
   Wait(()=>File.Exists(launched),"Selected app did not launch");
   Console.WriteLine("CHECK: app shortcut removed from original location, launches from storage, and restores");
   shortcutFixture=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),"Calculator Hidden Shortcut Fixture.lnk");MakeShortcut(shortcutFixture,fixture);SetEdit(window,"Calculator Hidden Shortcut Fixture");Click(window,"Refresh apps");Wait(()=>HasLabel(window,"1 apps · All Windows apps includes registered Store apps."),"Shortcut fixture did not appear");
   SelectFirstRow(window);Click(window,"Hide app shortcut");Wait(()=>!File.Exists(shortcutFixture),"App shortcut remained at original location");if(!File.Exists(fixture))throw new Exception("Installed program was moved with shortcut");
   Click(window,"Hidden files/apps");Wait(()=>HasLabel(window,"1 hidden items"),"Hidden app shortcut missing");if(File.Exists(launched))File.Delete(launched);SelectFirstRow(window);Click(window,"Open hidden item");Wait(()=>File.Exists(launched),"Hidden app shortcut did not launch");
   SelectFirstRow(window);Click(window,"Restore selected");Wait(()=>File.Exists(shortcutFixture),"App shortcut did not restore");File.Delete(shortcutFixture);Click(window,"Apps");
   Console.WriteLine("CHECK: persistent window actions while browsing apps");
   RequireQuickControls(window);Click(window,"Refresh windows");SelectQuickTarget(window,target.Text);Click(window,"Hide window");Wait(()=>!IsWindowVisible(target.Handle),"Persistent hide failed on Apps page");
   Click(window,"Restore all windows");Wait(()=>IsWindowVisible(target.Handle),"Persistent restore all failed on Apps page");if(!HasLabel(window,"Your apps"))throw new Exception("Restore action navigated away from Apps");
   Click(window,"Windows");Wait(()=>HasLabel(window,"Private window panel"),"Windows page missing");
   Console.WriteLine("CHECK: hide and restore");SelectTarget(window,target.Text);Click(window,"Hide selected");Wait(()=>!IsWindowVisible(target.Handle),"Hide selected did not hide the test window");
   Click(window,"Restore all");Wait(()=>IsWindowVisible(target.Handle),"Restore all did not restore the test window");
   Click(window,"Lock");if(!HasLabel(window,"Scientific"))throw new Exception("Lock did not restore calculator view");
   Click(window,"C");foreach(char c in "072839")Click(window,c.ToString());Click(window,"=");SelectTarget(window,target.Text);Click(window,"Hide selected");Wait(()=>!IsWindowVisible(target.Handle),"Second hide failed");
   Console.WriteLine("CHECK: crash recovery");app.Kill();app.WaitForExit();Wait(()=>IsWindowVisible(target.Handle),"Recovery monitor did not restore the test window after process termination",20);
   File.WriteAllText("calculator-windows-smoke.json","{\"ok\":true,\"startup\":true,\"arithmetic\":true,\"download_pin\":true,\"hide_restore\":true,\"lock\":true,\"crash_recovery\":true}");
   Console.WriteLine("PASS: visible calculator startup, 2+2=4, scientific functions, files/folders moved out of original locations, legacy migration, no-overwrite restore, restart recovery, file navigation, hidden app shortcut launch/restore, app launch, persistent hide/restore on Files and Apps, configured PIN, hide/restore, lock and crash recovery.");return 0;
  }catch(Exception e){Console.Error.WriteLine(e);try{string log=Path.Combine(testDataDir??Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CalculatorVault"),"startup-error.log");if(File.Exists(log)){File.Copy(log,"calculator-startup-error.log",true);Console.Error.WriteLine(File.ReadAllText(log));}}catch{}return 1;}
  finally{try{if(shortcutFixture!=null)File.Delete(shortcutFixture);if(fixture!=null)File.Delete(fixture);}catch{}if(app!=null&&!app.HasExited){app.Kill();app.WaitForExit();}if(target!=null){target.Show();target.Close();}}
 }
}
