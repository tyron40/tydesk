using System;
using System.IO;
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using System.Collections.Generic;
using System.Globalization;

partial class Calculator {
 Panel windowsPage=new Panel(),filesPage=new Panel(),appsPage=new Panel();
 TextBox address=new TextBox(),appSearch=new TextBox();
 ListView fileList=new ListView(),appList=new ListView();
 Label fileStatus=new Label(),appStatus=new Label();ComboBox drives=new ComboBox(),quickRunning=new ComboBox(),quickHidden=new ComboBox();
 string currentFolder="";bool degrees=true;Button angleButton;List<string> appPaths=new List<string>();
 Label Caption(Control parent,string text,int x,int y,int size){var l=new Label{Text=text,AutoSize=true,Location=new Point(x,y),Font=new Font("Segoe UI Semibold",size)};parent.Controls.Add(l);return l;}
 void BuildDashboard(){
  var side=new Panel{Dock=DockStyle.Left,Width=190,AutoScroll=true,AutoScrollMinSize=new Size(170,710),BackColor=Color.FromArgb(19,29,45)};vault.Controls.Add(side);
  Caption(side,"S / C",24,30,24);Caption(side,"YOUR WORKSPACE",24,85,9).ForeColor=Color.FromArgb(134,157,185);
  ButtonAt(side,"Windows",18,140,154,48).Click+=delegate{ShowPage(windowsPage);RefreshWindows();};
  ButtonAt(side,"Files",18,200,154,48).Click+=delegate{ShowPage(filesPage);};
  ButtonAt(side,"Apps",18,260,154,48).Click+=delegate{ShowPage(appsPage);LoadApps();};
  ButtonAt(side,"Refresh windows",18,315,154,30).Click+=delegate{RefreshWindows();};
  QuickChoice(side,quickRunning,"Running window",355);
  ButtonAt(side,"Hide window",18,392,154,36).Click+=delegate{SelectQuick(quickRunning,visible);HideSelected();};
  QuickChoice(side,quickHidden,"Hidden window",440);
  ButtonAt(side,"Restore window",18,477,154,36).Click+=delegate{SelectQuick(quickHidden,hidden);RestoreSelected();};
  ButtonAt(side,"Restore all windows",18,523,154,36).Click+=delegate{RestoreAll();};
  ButtonAt(side,"PIN settings",18,580,154,42).Click+=delegate{OpenPath("https://zdesk-nnym.onrender.com/#calculator-settings");};
  ButtonAt(side,"Lock",18,640,154,48).Click+=delegate{Lock();};
  var body=new Panel{Dock=DockStyle.Fill,Padding=new Padding(24)};vault.Controls.Add(body);body.BringToFront();
  foreach(var page in new[]{windowsPage,filesPage,appsPage}){page.Dock=DockStyle.Fill;page.AutoScroll=true;page.AutoScrollMinSize=new Size(748,670);body.Controls.Add(page);}
  Caption(windowsPage,"Private window panel",0,0,24);Caption(windowsPage,"Keep your workspace focused. Restore windows at any time.",0,48,10);
  Caption(windowsPage,"RUNNING WINDOWS",0,95,9);visible.SetBounds(0,122,748,160);StyleList(visible);windowsPage.Controls.Add(visible);
  ButtonAt(windowsPage,"Refresh",0,294,130,42).Click+=delegate{RefreshWindows();};ButtonAt(windowsPage,"Hide selected",142,294,180,42).Click+=delegate{HideSelected();};
  Caption(windowsPage,"HIDDEN WINDOWS",0,358,9);hidden.SetBounds(0,384,748,140);StyleList(hidden);windowsPage.Controls.Add(hidden);
  ButtonAt(windowsPage,"Restore selected",0,536,180,42).Click+=delegate{RestoreSelected();};ButtonAt(windowsPage,"Restore all",192,536,150,42).Click+=delegate{RestoreAll();};
  recoveryStatus.Text="Emergency restore: Ctrl + Alt + Shift + R";recoveryStatus.SetBounds(0,596,748,30);recoveryStatus.ForeColor=Color.FromArgb(134,157,185);windowsPage.Controls.Add(recoveryStatus);
  Caption(filesPage,"Your files",0,0,24);Caption(filesPage,"Browse folders and open files with their default Windows app.",0,48,10);
  string[] names={"Home","Desktop","Documents","Downloads"};string[] paths={Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"Downloads")};
  for(int i=0;i<names.Length;i++){string folder=paths[i];ButtonAt(filesPage,names[i],i*132,89,122,38).Click+=delegate{BrowseFolder(folder);};}
  drives.SetBounds(540,94,208,32);drives.DropDownStyle=ComboBoxStyle.DropDownList;foreach(var drive in DriveInfo.GetDrives())drives.Items.Add(drive.Name);filesPage.Controls.Add(drives);drives.SelectedIndexChanged+=delegate{if(drives.SelectedItem!=null)BrowseFolder(drives.SelectedItem.ToString());};
  ButtonAt(filesPage,"Up",0,142,64,38).Click+=delegate{try{var parent=Directory.GetParent(currentFolder);if(parent!=null)BrowseFolder(parent.FullName);}catch(Exception e){fileStatus.Text=e.Message;}};
  address.SetBounds(76,148,582,32);address.AccessibleName="Folder path";filesPage.Controls.Add(address);address.KeyDown+=delegate(object sender,KeyEventArgs e){if(e.KeyCode==Keys.Enter){BrowseFolder(address.Text);e.SuppressKeyPress=true;}};
  ButtonAt(filesPage,"Go",670,142,78,38).Click+=delegate{BrowseFolder(address.Text);};
  SetupView(fileList,filesPage,198);fileList.Columns.Add("Name",380);fileList.Columns.Add("Type",150);fileList.Columns.Add("Size",160);fileList.DoubleClick+=delegate{OpenFileSelection();};
  ButtonAt(filesPage,"Open selected",0,580,160,42).Click+=delegate{OpenFileSelection();};ButtonAt(filesPage,"Open in Explorer",172,580,180,42).Click+=delegate{OpenPath(currentFolder);};fileStatus.SetBounds(0,636,748,30);filesPage.Controls.Add(fileStatus);
  Caption(appsPage,"Your apps",0,0,24);Caption(appsPage,"Launch Start menu apps or browse for a program on this PC.",0,48,10);
  appSearch.SetBounds(0,96,440,32);appSearch.AccessibleName="Search apps";appsPage.Controls.Add(appSearch);appSearch.TextChanged+=delegate{FilterApps();};
  ButtonAt(appsPage,"Refresh apps",452,89,140,42).Click+=delegate{LoadApps();};ButtonAt(appsPage,"All Windows apps",604,89,144,42).Click+=delegate{OpenPath("shell:AppsFolder");};
  SetupView(appList,appsPage,154);appList.Height=405;appList.Columns.Add("App",350);appList.Columns.Add("Location",370);appList.DoubleClick+=delegate{LaunchSelectedApp();};
  ButtonAt(appsPage,"Launch selected",0,580,170,42).Click+=delegate{LaunchSelectedApp();};ButtonAt(appsPage,"Browse for app",182,580,170,42).Click+=delegate{using(var dialog=new OpenFileDialog{Title="Choose an app",Filter="Windows programs (*.exe;*.lnk;*.appref-ms)|*.exe;*.lnk;*.appref-ms|All files (*.*)|*.*"})if(dialog.ShowDialog(this)==DialogResult.OK)OpenPath(dialog.FileName);};
  appStatus.SetBounds(0,636,748,30);appsPage.Controls.Add(appStatus);
  BrowseFolder(paths[0]);ShowPage(windowsPage);
 }
 void QuickChoice(Control parent,ComboBox choice,string label,int top){
  choice.SetBounds(18,top,154,30);choice.DropDownStyle=ComboBoxStyle.DropDownList;choice.DropDownWidth=560;choice.AccessibleName=label;choice.BackColor=Color.FromArgb(30,41,58);choice.ForeColor=ForeColor;parent.Controls.Add(choice);
  choice.DropDown+=delegate{RefreshWindows();};
 }
 void SelectQuick(ComboBox choice,ListBox list){int index=choice.SelectedIndex;if(index<0||index>=choice.Items.Count){list.SelectedIndex=-1;return;}var entry=choice.Items[index] as Entry;list.SelectedIndex=-1;for(int i=0;i<list.Items.Count;i++){var candidate=list.Items[i] as Entry;if(candidate!=null&&entry!=null&&candidate.Handle==entry.Handle){list.SelectedIndex=i;break;}}}
 void SyncQuickChoices(){
  FillQuick(quickRunning,visible);FillQuick(quickHidden,hidden);
 }
 void FillQuick(ComboBox choice,ListBox source){
  long handle=0;int oldIndex=choice.SelectedIndex;if(oldIndex>=0&&oldIndex<choice.Items.Count){var previous=choice.Items[oldIndex] as Entry;if(previous!=null)handle=previous.Handle;}
  choice.BeginUpdate();choice.Items.Clear();int selected=-1;foreach(var item in source.Items){var entry=item as Entry;int index=choice.Items.Add(item);if(entry!=null&&entry.Handle==handle)selected=index;}
  choice.SelectedIndex=selected>=0?selected:(choice.Items.Count>0?0:-1);choice.Enabled=choice.Items.Count>0;choice.EndUpdate();
 }
 void StyleList(ListBox list){list.BackColor=Color.FromArgb(22,33,49);list.ForeColor=ForeColor;list.BorderStyle=BorderStyle.None;list.IntegralHeight=false;list.ItemHeight=24;}
 void SetupView(ListView view,Control parent,int top){view.SetBounds(0,top,748,365);view.View=View.Details;view.FullRowSelect=true;view.MultiSelect=false;view.HideSelection=false;view.BackColor=Color.FromArgb(22,33,49);view.ForeColor=ForeColor;view.BorderStyle=BorderStyle.None;parent.Controls.Add(view);}
 void ShowPage(Panel page){foreach(var p in new[]{windowsPage,filesPage,appsPage})p.Visible=p==page;page.BringToFront();RefreshWindows();}
 void BrowseFolder(string path){try{
  string full=Path.GetFullPath(Environment.ExpandEnvironmentVariables(path));var directory=new DirectoryInfo(full);
  var folders=directory.GetDirectories();var files=directory.GetFiles();Array.Sort(folders,(a,b)=>StringComparer.OrdinalIgnoreCase.Compare(a.Name,b.Name));Array.Sort(files,(a,b)=>StringComparer.OrdinalIgnoreCase.Compare(a.Name,b.Name));
  fileList.BeginUpdate();fileList.Items.Clear();foreach(var folder in folders){var row=new ListViewItem(folder.Name);row.SubItems.Add("Folder");row.SubItems.Add("");row.Tag=folder.FullName;fileList.Items.Add(row);}foreach(var file in files){var row=new ListViewItem(file.Name);row.SubItems.Add(file.Extension.Length==0?"File":file.Extension);try{row.SubItems.Add(file.Length<1024?file.Length+" B":(file.Length/1024d).ToString("N1")+" KB");}catch{row.SubItems.Add("");}row.Tag=file.FullName;fileList.Items.Add(row);}fileList.EndUpdate();currentFolder=full;address.Text=full;fileStatus.Text=folders.Length+" folders · "+files.Length+" files";
 }catch(Exception e){fileList.EndUpdate();fileStatus.Text="Cannot open folder: "+e.Message;}}
 void OpenFileSelection(){if(fileList.SelectedItems.Count==0)return;string path=fileList.SelectedItems[0].Tag as string;if(Directory.Exists(path))BrowseFolder(path);else OpenPath(path);}
 void OpenPath(string path){try{if(!string.IsNullOrEmpty(path))Process.Start(new ProcessStartInfo(path){UseShellExecute=true});}catch(Exception e){MessageBox.Show(this,e.Message,"Unable to open",MessageBoxButtons.OK,MessageBoxIcon.Information);}}
 void CollectApps(string folder){try{foreach(string path in Directory.GetFiles(folder)){string extension=Path.GetExtension(path).ToLowerInvariant();if(extension==".lnk"||extension==".appref-ms"||extension==".exe")appPaths.Add(path);}foreach(string child in Directory.GetDirectories(folder)){if((File.GetAttributes(child)&FileAttributes.ReparsePoint)==0)CollectApps(child);}}catch{}}
 void LoadApps(){appPaths.Clear();CollectApps(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu));CollectApps(Environment.GetFolderPath(Environment.SpecialFolder.CommonStartMenu));appPaths.Sort(StringComparer.OrdinalIgnoreCase);FilterApps();}
 void FilterApps(){appList.BeginUpdate();appList.Items.Clear();foreach(string path in appPaths){string name=Path.GetFileNameWithoutExtension(path);if(name.IndexOf(appSearch.Text,StringComparison.OrdinalIgnoreCase)<0)continue;var row=new ListViewItem(name);row.SubItems.Add(Path.GetDirectoryName(path));row.Tag=path;appList.Items.Add(row);}appList.EndUpdate();appStatus.Text=appList.Items.Count+" apps · All Windows apps includes registered Store apps.";}
 void LaunchSelectedApp(){if(appList.SelectedItems.Count>0)OpenPath(appList.SelectedItems[0].Tag as string);}
 bool Scientific(string k){
  if(k=="DEG"){degrees=!degrees;angleButton.Text=degrees?"DEG":"RAD";return true;}
  if(k=="pi"||k=="e"){input=(k=="pi"?Math.PI:Math.E).ToString("G15",CultureInfo.InvariantCulture);display.Text=input;resultShown=true;return true;}
  if(k!="sin"&&k!="cos"&&k!="tan"&&k!="sqrt"&&k!="x²"&&k!="log"&&k!="ln"&&k!="n!"&&k!="1/x"&&k!="abs"&&k!="10^x"&&k!="exp")return false;
  try{double value=Evaluate(input.Length==0?"0":input);double rad=degrees?value*Math.PI/180:value;
   switch(k){case "sin":value=Math.Sin(rad);break;case "cos":value=Math.Cos(rad);break;case "tan":if(Math.Abs(Math.Cos(rad))<1e-14)throw new Exception();value=Math.Tan(rad);break;case "sqrt":value=Math.Sqrt(value);break;case "x²":value*=value;break;case "log":value=Math.Log10(value);break;case "ln":value=Math.Log(value);break;case "1/x":value=1/value;break;case "abs":value=Math.Abs(value);break;case "10^x":value=Math.Pow(10,value);break;case "exp":value=Math.Exp(value);break;case "n!":if(value<0||value>170||value!=Math.Floor(value))throw new Exception();double fact=1;for(int i=2;i<=value;i++)fact*=i;value=fact;break;}
   if(double.IsNaN(value)||double.IsInfinity(value))throw new Exception();input=value.ToString("G15",CultureInfo.InvariantCulture);display.Text=input;resultShown=true;
  }catch{input="";display.Text="Error";resultShown=true;}return true;
 }
}
