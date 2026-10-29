using System;
using System.IO;
using System.Text;
using System.Drawing;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.ComponentModel;

class VaultItem {
 public string Id,Original,Stored,Kind,State;public int Attributes;public bool Legacy;
 public string Line(){return Id+"|"+Encode(Original)+"|"+Encode(Stored)+"|"+Kind+"|"+Attributes+"|"+(Legacy?"1":"0")+"|"+State;}
 public static string Encode(string text){return Convert.ToBase64String(Encoding.UTF8.GetBytes(text??""));}
 public static string Decode(string text){return Encoding.UTF8.GetString(Convert.FromBase64String(text));}
 public static VaultItem Parse(string line){string[] a=line.Split('|');Guid id;if(a.Length!=7||!Guid.TryParseExact(a[0],"N",out id))throw new IOException("Invalid hidden item record.");var item=new VaultItem{Id=a[0],Original=Decode(a[1]),Stored=Decode(a[2]),Kind=a[3],Attributes=int.Parse(a[4]),Legacy=a[5]=="1",State=a[6]};if(!Path.IsPathRooted(item.Original)||(!item.Legacy&&!Path.IsPathRooted(item.Stored)))throw new IOException("Invalid hidden item path.");return item;}
}
partial class Calculator {
 Panel hiddenFilesPage=new Panel();ListView hiddenFileList=new ListView();Label hiddenFileStatus=new Label();
 List<VaultItem> vaultItems=new List<VaultItem>();string vaultState=Path.Combine(Program.Dir,"vault-items-v2.txt"),legacyState=Path.Combine(Program.Dir,"hidden-files-v1.txt");string vaultReadError="";
 bool PathExists(string path){return File.Exists(path)||Directory.Exists(path);}
 bool Within(string path,string parent){string full=Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar),root=Path.GetFullPath(parent).TrimEnd(Path.DirectorySeparatorChar);return full.Equals(root,StringComparison.OrdinalIgnoreCase)||full.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase);}
 void BuildHiddenFiles(){
  try{
   if(File.Exists(vaultState)){foreach(string line in File.ReadAllLines(vaultState))if(line.Length>0)vaultItems.Add(VaultItem.Parse(line));}
   else if(File.Exists(legacyState)){
    foreach(string line in File.ReadAllLines(legacyState)){string path=VaultItem.Decode(line);if(!Path.IsPathRooted(path)||vaultItems.Exists(v=>v.Original.Equals(path,StringComparison.OrdinalIgnoreCase)))continue;int attrs=0;try{attrs=(int)File.GetAttributes(path);}catch{}vaultItems.Add(new VaultItem{Id=Guid.NewGuid().ToString("N"),Original=path,Stored="",Kind=(attrs&(int)FileAttributes.Directory)!=0?"Folder":"File",Attributes=attrs,Legacy=true,State="Legacy"});}
    SaveVault();
   }
   // A successful atomic restore may have completed before the index was updated.
   bool changed=false;foreach(var item in new List<VaultItem>(vaultItems))if(item.State=="Restoring"&&!PathExists(item.Stored)&&PathExists(item.Original)){try{EnsureRestoredAttributes(item);vaultItems.Remove(item);changed=true;}catch{}}if(changed)SaveVault();
  }catch(Exception e){vaultReadError="Hidden item index could not be read: "+e.Message;}
  Caption(hiddenFilesPage,"Hidden files/apps",0,0,24);Caption(hiddenFilesPage,"Moved items are removed from their original folders. Restore them below.",0,48,10);
  Caption(hiddenFilesPage,"App shortcuts can be hidden; installed programs remain installed. Storage is not encrypted.",0,73,9);
  SetupView(hiddenFileList,hiddenFilesPage,110);hiddenFileList.Height=405;hiddenFileList.MultiSelect=true;hiddenFileList.Columns.Add("Name",175);hiddenFileList.Columns.Add("Type",105);hiddenFileList.Columns.Add("Original location",325);hiddenFileList.Columns.Add("Status",120);
  ButtonAt(hiddenFilesPage,"Open hidden item",0,536,170,42).Click+=delegate{OpenHiddenSelection();};
  ButtonAt(hiddenFilesPage,"Restore selected",182,536,170,42).Click+=delegate{RestoreVault(SelectedVault());};
  ButtonAt(hiddenFilesPage,"Restore all items",364,536,170,42).Click+=delegate{RestoreVault(new List<VaultItem>(vaultItems));};
  ButtonAt(hiddenFilesPage,"Back to files",546,536,190,42).Click+=delegate{if(Directory.Exists(currentFolder))BrowseFolder(currentFolder);ShowPage(filesPage);};
  ButtonAt(hiddenFilesPage,"Move old hidden items",0,590,220,42).Click+=delegate{MoveLegacySelection();};
  ButtonAt(hiddenFilesPage,"Refresh hidden items",232,590,210,42).Click+=delegate{RefreshHiddenFiles();};
  hiddenFileStatus.SetBounds(0,646,748,40);hiddenFilesPage.Controls.Add(hiddenFileStatus);RefreshHiddenFiles();
 }
 void SaveVault(){
  if(vaultReadError.Length>0)throw new IOException(vaultReadError);
  Directory.CreateDirectory(Program.Dir);string tmp=vaultState+".tmp";var lines=new List<string>();foreach(var item in vaultItems)lines.Add(item.Line());File.WriteAllLines(tmp,lines.ToArray());if(File.Exists(vaultState))File.Replace(tmp,vaultState,null);else File.Move(tmp,vaultState);
 }
 string StorageRoot(string source){
  string sourceRoot=Path.GetPathRoot(Path.GetFullPath(source)),dataRoot=Path.GetPathRoot(Path.GetFullPath(Program.Dir));
  string root;
  if(sourceRoot.Equals(dataRoot,StringComparison.OrdinalIgnoreCase))root=Path.Combine(Program.Dir,"Storage");
  else{string user;using(var sha=SHA256.Create())user=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)))).Replace("-","").Substring(0,16);root=Path.Combine(sourceRoot,".SystemCalculatorStorage-"+user);}
  Directory.CreateDirectory(root);File.SetAttributes(root,File.GetAttributes(root)|FileAttributes.Hidden);return root;
 }
 bool IsProtectedFilePath(string path){
  string full=Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
  if(full.Equals(Path.GetPathRoot(path).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase))return true;
  foreach(string protectedPath in new[]{Program.Dir,Application.ExecutablePath,Environment.GetFolderPath(Environment.SpecialFolder.Windows),Environment.GetFolderPath(Environment.SpecialFolder.System),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86)}){
   if(string.IsNullOrEmpty(protectedPath))continue;
   if(Within(full,protectedPath)||Within(protectedPath,full))return true;
  }return false;
 }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool MoveFileEx(string from,string to,uint flags);
 string NativePath(string path){if(path.StartsWith(@"\\?\"))return path;return path.StartsWith(@"\\")?@"\\?\UNC\"+path.Substring(2):@"\\?\"+path;}
 void MoveItem(string from,string to,bool folder){if(!MoveFileEx(NativePath(from),NativePath(to),8))throw new Win32Exception(Marshal.GetLastWin32Error());}
 VaultItem StorePath(string path,string kind,VaultItem legacy){
  path=Path.GetFullPath(path);if(IsProtectedFilePath(path))throw new IOException("System and calculator folders cannot be moved.");
  FileAttributes attrs=File.GetAttributes(path);if((attrs&FileAttributes.ReparsePoint)!=0)throw new IOException("Choose the original item instead of a linked folder.");
  bool folder=(attrs&FileAttributes.Directory)!=0;
  string root=StorageRoot(path);if(Within(path,root)||Within(root,path))throw new IOException("Calculator storage cannot be hidden again.");
  var item=legacy??new VaultItem{Id=Guid.NewGuid().ToString("N"),Original=path,Kind=kind??(folder?"Folder":"File"),Attributes=(int)attrs};
  bool wasLegacy=item.Legacy;if(wasLegacy)item.Attributes=(int)(attrs&~FileAttributes.Hidden);
  string bucket=Path.Combine(root,item.Id);Directory.CreateDirectory(bucket);item.Stored=Path.Combine(bucket,Path.GetFileName(path));item.Legacy=false;item.State="Pending";
  if(legacy==null)vaultItems.Add(item);
  try{SaveVault();}catch{if(legacy==null)vaultItems.Remove(item);else{item.Legacy=wasLegacy;item.State="Legacy";item.Stored="";}throw;}
  // Both paths are on the same volume. Rename atomically; never copy/delete a tree.
  try{MoveItem(path,item.Stored,folder);}
  catch{
   if(PathExists(path)&&!PathExists(item.Stored)){if(legacy==null)vaultItems.Remove(item);else{item.Legacy=wasLegacy;item.State="Legacy";item.Stored="";}SaveVault();try{Directory.Delete(bucket);}catch{}}
   throw;
  }
  if(wasLegacy){item.Attributes=(int)(attrs&~FileAttributes.Hidden);try{File.SetAttributes(item.Stored,attrs&~FileAttributes.Hidden);}catch{}}
  item.State="Stored";SaveVault();return item;
 }
 List<VaultItem> SelectedVault(){var items=new List<VaultItem>();foreach(ListViewItem row in hiddenFileList.SelectedItems)items.Add((VaultItem)row.Tag);return items;}
 void HideFileSelection(){
  if(fileList.SelectedItems.Count==0){fileStatus.Text="Select a file or folder, then choose Hide selected.";return;}
  var paths=new List<string>();foreach(ListViewItem row in fileList.SelectedItems)paths.Add((string)row.Tag);int count=0;var errors=new List<string>();
  foreach(string path in paths)try{string ext=Path.GetExtension(path).ToLowerInvariant();StorePath(path,ext==".lnk"||ext==".appref-ms"?"App shortcut":null,null);count++;}catch(Exception e){errors.Add(Path.GetFileName(path)+": "+e.Message);}
  BrowseFolder(currentFolder);RefreshHiddenFiles();fileStatus.Text=count+" moved to Hidden files/apps."+(errors.Count>0?" "+errors.Count+" could not be moved.":"");ShowVaultErrors(errors);
 }
 void HideAppSelection(){
  if(appList.SelectedItems.Count==0){appStatus.Text="Select an app shortcut, then choose Hide app shortcut.";return;}
  string path=appList.SelectedItems[0].Tag as string;string ext=Path.GetExtension(path).ToLowerInvariant();
  if(ext!=".lnk"&&ext!=".appref-ms"){appStatus.Text="Only app shortcuts can be hidden here. Installed program files are not moved.";return;}
  try{StorePath(path,"App shortcut",null);LoadApps();RefreshHiddenFiles();appStatus.Text="Shortcut moved to Hidden files/apps. The program remains installed.";}catch(Exception e){appStatus.Text="Shortcut could not be moved: "+e.Message;}
 }
 void MoveLegacySelection(){
  var selected=SelectedVault();var errors=new List<string>();int count=0;
  foreach(var item in selected)if(item.Legacy)try{StorePath(item.Original,item.Kind,item);count++;}catch(Exception e){errors.Add(Path.GetFileName(item.Original)+": "+e.Message);}
  RefreshHiddenFiles();if(Directory.Exists(currentFolder))BrowseFolder(currentFolder);hiddenFileStatus.Text=count+" old hidden items moved into storage.";ShowVaultErrors(errors);
 }
 void RefreshHiddenFiles(){
  hiddenFileList.BeginUpdate();hiddenFileList.Items.Clear();
  foreach(var item in vaultItems){
   string status;
   if(item.Legacy)status=PathExists(item.Original)?"Old hidden setting":"Not found";
   else if(PathExists(item.Stored))status=PathExists(item.Original)?"Original also exists":"In storage";
   else status=PathExists(item.Original)?"Original still present":"Unavailable";
   var row=new ListViewItem(Path.GetFileName(item.Original));row.SubItems.Add(item.Kind);row.SubItems.Add(item.Original);row.SubItems.Add(status);row.Tag=item;hiddenFileList.Items.Add(row);
  }hiddenFileList.EndUpdate();hiddenFileStatus.Text=vaultReadError.Length>0?vaultReadError:vaultItems.Count+" hidden items";
 }
 void OpenHiddenSelection(){var selected=SelectedVault();if(selected.Count==0)return;var item=selected[0];OpenPath(item.Legacy?item.Original:item.Stored);}
 void EnsureRestoredAttributes(VaultItem item){FileAttributes attrs=File.GetAttributes(item.Original);if((item.Attributes&(int)FileAttributes.Hidden)==0&&(attrs&FileAttributes.Hidden)!=0)File.SetAttributes(item.Original,attrs&~FileAttributes.Hidden);}
 void RestoreVault(List<VaultItem> items){
  int count=0;var errors=new List<string>();
  foreach(var item in items)try{
   if(vaultReadError.Length>0)throw new IOException(vaultReadError);
   if(item.Legacy){File.SetAttributes(item.Original,File.GetAttributes(item.Original)&~FileAttributes.Hidden);}
   else if(!PathExists(item.Stored)){
    if((item.State!="Pending"&&item.State!="Restoring")||!PathExists(item.Original))throw new IOException("Stored item is unavailable; its recovery record has been kept.");if(item.State=="Restoring")EnsureRestoredAttributes(item);
   }else{
    if(PathExists(item.Original))throw new IOException("The original location is occupied. Rename or move that item first; nothing was overwritten.");
    Directory.CreateDirectory(Path.GetDirectoryName(item.Original));item.State="Restoring";SaveVault();
    MoveItem(item.Stored,item.Original,(item.Attributes&(int)FileAttributes.Directory)!=0);
    // Old attribute-only items should be visible after they are restored.
    EnsureRestoredAttributes(item);
   }
   vaultItems.Remove(item);try{SaveVault();}catch{vaultItems.Add(item);throw;}
   if(!item.Legacy&&!string.IsNullOrEmpty(item.Stored))try{Directory.Delete(Path.GetDirectoryName(item.Stored));}catch{}
   count++;
  }catch(Exception e){errors.Add(Path.GetFileName(item.Original)+": "+e.Message);}
  RefreshHiddenFiles();if(Directory.Exists(currentFolder))BrowseFolder(currentFolder);LoadApps();hiddenFileStatus.Text=count+" restored."+(errors.Count>0?" "+errors.Count+" could not be restored; their records were kept.":"");ShowVaultErrors(errors);
 }
 void ShowVaultErrors(List<string> errors){if(errors.Count>0)MessageBox.Show(this,string.Join(Environment.NewLine,errors.ToArray()),"Some items could not be changed",MessageBoxButtons.OK,MessageBoxIcon.Information);}
}
