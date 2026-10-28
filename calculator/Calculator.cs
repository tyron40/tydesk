using System;
using System.IO;
using System.Text;
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Threading;
using System.Globalization;

static class Native {
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern uint RegisterWindowMessage(string name);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint message,IntPtr w,IntPtr l);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 public delegate bool Callback(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Callback c, IntPtr p);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder b, int n);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder b, int n);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr h, int cmd);
 [DllImport("user32.dll")] public static extern bool RegisterHotKey(IntPtr h,int id,uint mods,uint key);
 [DllImport("user32.dll")] public static extern bool UnregisterHotKey(IntPtr h,int id);
}
class Entry {
 public long Handle; public int Pid; public long Started; public string Title;
 public override string ToString(){return Title;}
 public bool Valid(){try {uint id; Native.GetWindowThreadProcessId(new IntPtr(Handle),out id); return Native.IsWindow(new IntPtr(Handle)) && id==Pid && Process.GetProcessById(Pid).StartTime.ToUniversalTime().Ticks==Started;}catch{return false;}}
 public string Line(){return Handle+"|"+Pid+"|"+Started;}
}
static class Program {
 public static string Dir=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"CalculatorVault");
 public static uint ShowMessage=Native.RegisterWindowMessage("SystemCalculator.ShowDesktopCalculator.v1");
 public static string State=Path.Combine(Dir,"windows.txt");
 public static List<Entry> Load(){var list=new List<Entry>();try{foreach(string line in File.ReadAllLines(State)){string[] a=line.Split('|');if(a.Length==3)list.Add(new Entry{Handle=long.Parse(a[0]),Pid=int.Parse(a[1]),Started=long.Parse(a[2])});}}catch{}return list;}
 public static byte[] ReadPinConfig(string path){
  try {using(var stream=File.OpenRead(path)){
   if(stream.Length<64)return null;
   stream.Seek(-64,SeekOrigin.End);byte[] block=new byte[64];int n=0;
   while(n<block.Length){int read=stream.Read(block,n,block.Length-n);if(read==0)return null;n+=read;}
   if(Encoding.ASCII.GetString(block,48,16)!="ZDESKCALCPIN0002")return null;
   byte[] data=new byte[48];Array.Copy(block,data,48);return data;
  }}catch{return null;}
 }
 public static void Recover(){foreach(Entry e in Load())if(e.Valid())Native.ShowWindowAsync(new IntPtr(e.Handle),9);}
 public static void Report(Exception error){
  string path=Path.Combine(Dir,"startup-error.log");
  try{Directory.CreateDirectory(Dir);File.WriteAllText(path,DateTime.UtcNow.ToString("O")+Environment.NewLine+error);}catch{}
  try{MessageBox.Show("System Calculator could not start.\n\n"+error.Message+"\n\nDetails: "+path,"System Calculator",MessageBoxButtons.OK,MessageBoxIcon.Error);}catch{}
 }
 [STAThread] public static void Main(string[] args){
  try{Run(args);}catch(Exception error){Report(error);}
 }
 static void Run(string[] args){
  Directory.CreateDirectory(Dir);
  if(args.Length==2 && args[0]=="/watch") {try{Process.GetProcessById(int.Parse(args[1])).WaitForExit();}catch{}Recover();return;}
  if(args.Length==1 && args[0]=="/restore"){Recover();return;}
  Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
  Application.ThreadException+=delegate(object sender,ThreadExceptionEventArgs e){Report(e.Exception);};
  AppDomain.CurrentDomain.UnhandledException+=delegate(object sender,UnhandledExceptionEventArgs e){Report(e.ExceptionObject as Exception??new Exception("Unhandled startup error"));};
  bool first; using(var mutex=new Mutex(true,"Local\\CalculatorVault_Tyron_v1",out first)){
   if(!first){bool found=false;Native.EnumWindows(delegate(IntPtr h,IntPtr unused){var text=new StringBuilder(256);Native.GetWindowText(h,text,256);if(text.ToString()=="System Calculator"){Native.ShowWindowAsync(h,9);Native.PostMessage(h,ShowMessage,IntPtr.Zero,IntPtr.Zero);Native.SetForegroundWindow(h);found=true;return false;}return true;},IntPtr.Zero);if(!found)MessageBox.Show("A previous System Calculator process is not responding. Close System Calculator in Task Manager, then open this file again.","System Calculator");return;}
   Recover();Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
   try{Application.Run(new Calculator());}finally{Recover();}
  }
 }

}
partial class Calculator:Form {
 TextBox display=new TextBox(); Panel calc=new Panel(),vault=new Panel(); ListBox visible=new ListBox(),hidden=new ListBox(); Label recoveryStatus=new Label();
 byte[] configuredPin=Program.ReadPinConfig(Application.ExecutablePath);
 List<Entry> entries=new List<Entry>(); bool resultShown=false; string input=""; string pinPath=Path.Combine(Program.Dir,"pin.dat");
 DateTime retry=DateTime.MinValue; int attempts=0; bool hotkey=false; Process watcher;
 public Calculator(){
  Text="System Calculator";try{Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);}catch{Icon=SystemIcons.Application;}
  ClientSize=new Size(520,630);FormBorderStyle=FormBorderStyle.FixedSingle;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;
  BackColor=Color.FromArgb(14,20,32);ForeColor=Color.FromArgb(234,240,250);Font=new Font("Segoe UI",10);
  calc.Dock=DockStyle.Fill;vault.Dock=DockStyle.Fill;Controls.Add(calc);Controls.Add(vault);vault.Visible=false;
  Caption(calc,"Scientific",22,20,18);Caption(calc,"SYSTEM CALCULATOR",24,60,8);
  display.ReadOnly=true;display.BorderStyle=BorderStyle.None;display.BackColor=BackColor;display.ForeColor=ForeColor;display.Text="0";display.TextAlign=HorizontalAlignment.Right;display.Font=new Font("Segoe UI Light",34);display.SetBounds(22,95,474,72);calc.Controls.Add(display);
  string[] keys={"DEG","sin","cos","tan","(",")","sqrt","x²","x^y","log","ln","DEL","pi","e","n!","1/x","%","C","7","8","9","/","abs","10^x","4","5","6","*","+/-","exp","1","2","3","-","0","."};
  for(int i=0;i<keys.Length;i++){string k=keys[i];var button=ButtonAt(calc,k,22+(i%6)*80,175+(i/6)*56,74,48);button.Click+=delegate{Press(k);};if(k=="DEG")angleButton=button;}
  string[] last={"C","DEL","+","="};for(int i=0;i<4;i++){string k=last[i];var button=ButtonAt(calc,k,22+i*120,533,114,62);button.Click+=delegate{Press(k);};if(k=="="){button.BackColor=Color.FromArgb(94,222,190);button.ForeColor=Color.FromArgb(10,36,32);}}
  BuildDashboard();
  var idle=new System.Windows.Forms.Timer{Interval=60000};idle.Tick+=delegate{if(vault.Visible)Lock();};idle.Start();
  Shown+=delegate{
   BeginInvoke(new Action(delegate{Show();WindowState=FormWindowState.Normal;BringToFront();Activate();Native.SetForegroundWindow(Handle);}));
   try{hotkey=Native.RegisterHotKey(Handle,1,0x4007,0x52);}catch{hotkey=false;}
   try{watcher=Process.Start(new ProcessStartInfo(Application.ExecutablePath,"/watch "+Process.GetCurrentProcess().Id){UseShellExecute=false,CreateNoWindow=true});}catch{}
  };
  KeyPreview=true;
  KeyPress+=delegate(object sender,KeyPressEventArgs e){
   if(!calc.Visible)return;
   if("0123456789.()+-*/^%=".IndexOf(e.KeyChar)>=0){Press(e.KeyChar.ToString());e.Handled=true;}
   else if(e.KeyChar=='\r'){Press("=");e.Handled=true;}
   else if(e.KeyChar=='\b'){Press("DEL");e.Handled=true;}
  };
  KeyDown+=delegate(object sender,KeyEventArgs e){if(calc.Visible&&(e.KeyCode==Keys.Escape||e.KeyCode==Keys.Delete)){Press("C");e.SuppressKeyPress=true;}};
  FormClosing+=delegate{RestoreAll();if(hotkey)Native.UnregisterHotKey(Handle,1);};
 }
 Button ButtonAt(Control parent,string text,int x,int y,int w,int h){var b=new Button{Text=text,FlatStyle=FlatStyle.Flat,BackColor=Color.FromArgb(30,41,58),Cursor=Cursors.Hand,ForeColor=Color.White};b.FlatAppearance.BorderSize=0;b.FlatAppearance.MouseOverBackColor=Color.FromArgb(46,65,88);b.SetBounds(x,y,w,h);parent.Controls.Add(b);return b;}
 protected override void WndProc(ref Message m){if((uint)m.Msg==Program.ShowMessage){Lock();Show();WindowState=FormWindowState.Normal;BringToFront();Activate();Native.SetForegroundWindow(Handle);}if(m.Msg==0x312){RestoreAll();Lock();}base.WndProc(ref m);}
 byte[] Hash(string pin,byte[] salt,bool modern){using(var k=modern?new Rfc2898DeriveBytes(pin,salt,210000,HashAlgorithmName.SHA256):new Rfc2898DeriveBytes(pin,salt,150000)){return k.GetBytes(32);}}
 bool Digits(string s){if(s==null||s.Length<6||s.Length>12)return false;foreach(char c in s)if(c<'0'||c>'9')return false;return true;}
 bool Unlock(string s){
  if(!Digits(s)||(configuredPin==null&&!File.Exists(pinPath))||DateTime.UtcNow<retry)return false;
  try{
   byte[] data=configuredPin??ProtectedData.Unprotect(File.ReadAllBytes(pinPath),null,DataProtectionScope.CurrentUser);
   if(data.Length!=48)return false;
   byte[] salt=new byte[16];Array.Copy(data,salt,16);byte[] hash=Hash(s,salt,configuredPin!=null);
   int diff=0;for(int i=0;i<32;i++)diff|=hash[i]^data[i+16];
   if(diff==0){attempts=0;ClientSize=new Size(Math.Min(1010,Screen.FromControl(this).WorkingArea.Width-40),Math.Min(740,Screen.FromControl(this).WorkingArea.Height-80));vault.Visible=true;calc.Visible=false;RefreshWindows();return true;}
   if(++attempts>=5){retry=DateTime.UtcNow.AddSeconds(30);attempts=0;}
  }catch{}return false;
 }
 void Press(string k){
  bool number=k=="("||k.Length==1&&((k[0]>='0'&&k[0]<='9')||k==".");
  if(number&&resultShown){input="";resultShown=false;}
  if(Scientific(k))return;
  if(k=="x^y")k="^";
  if(k=="C"){input="";resultShown=false;}
  else if(k=="DEL"){if(input.Length>0)input=input.Substring(0,input.Length-1);resultShown=false;}
  else if(k=="="){
   if(Unlock(input)){input="";resultShown=false;display.Text="0";return;}
   try{input=Evaluate(input).ToString("G15",CultureInfo.InvariantCulture);resultShown=true;}
   catch{input="";resultShown=true;display.Text="Error";return;}
  }else if(k=="+/-"){if(input.StartsWith("-"))input=input.Substring(1);else input="-"+input;}
  else if(k=="%") {try{input=(Evaluate(input)/100).ToString("G15",CultureInfo.InvariantCulture);resultShown=true;}catch{input="";resultShown=true;}}
  else if(input.Length<80){input+=k;resultShown=false;}
  display.Text=input.Length==0?"0":input;
 }
 // Arithmetic parser: parentheses are internal only; no code evaluation.
 double Evaluate(string s){int p=0;double v=Expr(s,ref p);if(p!=s.Length||double.IsNaN(v)||double.IsInfinity(v))throw new Exception();return v;}
 double Expr(string s,ref int p){double v=Term(s,ref p);while(p<s.Length&&(s[p]=='+'||s[p]=='-')){char op=s[p++];double b=Term(s,ref p);v=op=='+'?v+b:v-b;}return v;}
 double Term(string s,ref int p){double v=Unary(s,ref p);while(p<s.Length&&(s[p]=='*'||s[p]=='/')){char op=s[p++];double b=Unary(s,ref p);v=op=='*'?v*b:v/b;}return v;}
 double Unary(string s,ref int p){if(p<s.Length&&(s[p]=='+'||s[p]=='-')){char sign=s[p++];double value=Unary(s,ref p);return sign=='-'?-value:value;}return Power(s,ref p);}
 double Power(string s,ref int p){double value=Number(s,ref p);if(p<s.Length&&s[p]=='^'){p++;value=Math.Pow(value,Unary(s,ref p));}return value;}
 double Number(string s,ref int p){if(p<s.Length&&s[p]=='('){p++;double value=Expr(s,ref p);if(p>=s.Length||s[p++]!=')')throw new Exception();return value;}int start=p;while(p<s.Length&&(char.IsDigit(s[p])||s[p]=='.'))p++;if(p<s.Length&&(s[p]=='E'||s[p]=='e')){p++;if(p<s.Length&&(s[p]=='+'||s[p]=='-'))p++;while(p<s.Length&&char.IsDigit(s[p]))p++;}return double.Parse(s.Substring(start,p-start),CultureInfo.InvariantCulture);}
 void Lock(){ClientSize=new Size(520,630);vault.Visible=false;calc.Visible=true;input="";resultShown=false;display.Text="0";}
 void RefreshWindows(){visible.SelectedIndex=-1;visible.Items.Clear();Native.EnumWindows(delegate(IntPtr h,IntPtr unused){uint pid;Native.GetWindowThreadProcessId(h,out pid);if(pid==Process.GetCurrentProcess().Id||!Native.IsWindowVisible(h))return true;var title=new StringBuilder(512);Native.GetWindowText(h,title,512);var cls=new StringBuilder(128);Native.GetClassName(h,cls,128);if(title.Length==0||cls.ToString()=="Shell_TrayWnd"||cls.ToString()=="Progman"||cls.ToString()=="WorkerW")return true;try{var process=Process.GetProcessById((int)pid);visible.Items.Add(new Entry{Handle=h.ToInt64(),Pid=(int)pid,Started=process.StartTime.ToUniversalTime().Ticks,Title=process.ProcessName+" - "+title});}catch{}return true;},IntPtr.Zero);SyncHidden();}
 void Save(){string tmp=Program.State+".tmp";var lines=new List<string>();foreach(Entry e in entries)lines.Add(e.Line());File.WriteAllLines(tmp,lines.ToArray());if(File.Exists(Program.State))File.Replace(tmp,Program.State,null);else File.Move(tmp,Program.State);}
 void SyncHidden(){hidden.SelectedIndex=-1;hidden.Items.Clear();foreach(Entry e in entries)hidden.Items.Add(e);SyncQuickChoices();}
 void HideSelected(){if(!hotkey||watcher==null||watcher.HasExited){recoveryStatus.Text="Hiding unavailable: shortcut or recovery monitor failed.";return;}int selected=visible.SelectedIndex;if(selected<0||selected>=visible.Items.Count)return;var e=visible.Items[selected] as Entry;if(e==null||!e.Valid())return;entries.Add(e);try{Save();}catch(Exception ex){entries.Remove(e);MessageBox.Show("Cannot save recovery information: "+ex.Message);return;}Native.ShowWindowAsync(new IntPtr(e.Handle),0);RefreshWindows();}
 void RestoreSelected(){int selected=hidden.SelectedIndex;if(selected<0||selected>=hidden.Items.Count)return;var e=hidden.Items[selected] as Entry;if(e==null)return;if(e.Valid())Native.ShowWindowAsync(new IntPtr(e.Handle),9);entries.Remove(e);try{Save();}catch{}RefreshWindows();}
 void RestoreAll(){foreach(Entry e in entries)if(e.Valid())Native.ShowWindowAsync(new IntPtr(e.Handle),9);entries.Clear();try{Save();}catch{}SyncHidden();}
}
