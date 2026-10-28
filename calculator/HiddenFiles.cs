using System;
using System.IO;
using System.Text;
using System.Drawing;
using System.Windows.Forms;
using System.Collections.Generic;

partial class Calculator {
 Panel hiddenFilesPage=new Panel();ListView hiddenFileList=new ListView();Label hiddenFileStatus=new Label();
 List<string> hiddenPaths=new List<string>();string hiddenFileState=Path.Combine(Program.Dir,"hidden-files-v1.txt");
 string hiddenFileReadError="";
 void BuildHiddenFiles(){
  try{if(File.Exists(hiddenFileState))foreach(string line in File.ReadAllLines(hiddenFileState)){string path=Encoding.UTF8.GetString(Convert.FromBase64String(line));if(Path.IsPathRooted(path)&&!hiddenPaths.Exists(p=>string.Equals(p,path,StringComparison.OrdinalIgnoreCase)))hiddenPaths.Add(path);}}
  catch(Exception e){hiddenFileReadError="Cannot read saved hidden files: "+e.Message;}
  Caption(hiddenFilesPage,"Hidden files",0,0,24);Caption(hiddenFilesPage,"Files stay in their original locations. Hiding does not encrypt them.",0,48,10);
  SetupView(hiddenFileList,hiddenFilesPage,95);hiddenFileList.Height=460;hiddenFileList.MultiSelect=true;hiddenFileList.Columns.Add("Name",190);hiddenFileList.Columns.Add("Original location",430);hiddenFileList.Columns.Add("Status",105);
  ButtonAt(hiddenFilesPage,"Unhide selected",0,580,170,42).Click+=delegate{var paths=new List<string>();foreach(ListViewItem item in hiddenFileList.SelectedItems)paths.Add((string)item.Tag);UnhideFiles(paths);};
  ButtonAt(hiddenFilesPage,"Unhide all",182,580,150,42).Click+=delegate{UnhideFiles(new List<string>(hiddenPaths));};
  ButtonAt(hiddenFilesPage,"Back to files",344,580,170,42).Click+=delegate{if(Directory.Exists(currentFolder))BrowseFolder(currentFolder);ShowPage(filesPage);};
  ButtonAt(hiddenFilesPage,"Refresh hidden files",526,580,210,42).Click+=delegate{RefreshHiddenFiles();};
  hiddenFileStatus.SetBounds(0,636,748,40);hiddenFilesPage.Controls.Add(hiddenFileStatus);RefreshHiddenFiles();
 }
 void SaveHiddenFiles(){
  if(hiddenFileReadError.Length>0)throw new IOException(hiddenFileReadError);
  Directory.CreateDirectory(Program.Dir);string tmp=hiddenFileState+".tmp";var lines=new List<string>();foreach(string path in hiddenPaths)lines.Add(Convert.ToBase64String(Encoding.UTF8.GetBytes(path)));
  File.WriteAllLines(tmp,lines.ToArray());if(File.Exists(hiddenFileState))File.Replace(tmp,hiddenFileState,null);else File.Move(tmp,hiddenFileState);
 }
 bool HasHiddenAttribute(string path){return (File.GetAttributes(path)&FileAttributes.Hidden)!=0;}
 bool IsProtectedFilePath(string path){
  string full=Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
  if(string.Equals(full,Path.GetPathRoot(path).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase))return true;
  foreach(string protectedPath in new[]{Program.Dir,Application.ExecutablePath,Environment.GetFolderPath(Environment.SpecialFolder.Windows),Environment.GetFolderPath(Environment.SpecialFolder.System),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86)}){
   if(string.IsNullOrEmpty(protectedPath))continue;string root=Path.GetFullPath(protectedPath).TrimEnd(Path.DirectorySeparatorChar);
   if(full.Equals(root,StringComparison.OrdinalIgnoreCase)||full.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||root.StartsWith(full+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))return true;
  }return false;
 }
 void HideFileSelection(){
  if(fileList.SelectedItems.Count==0){fileStatus.Text="Select a file or folder, then choose Hide selected.";return;}
  var paths=new List<string>();foreach(ListViewItem item in fileList.SelectedItems)paths.Add((string)item.Tag);
  int count=0;var errors=new List<string>();
  foreach(string path in paths)try{
   if(IsProtectedFilePath(path))throw new IOException("System and calculator folders cannot be hidden.");
   FileAttributes attrs=File.GetAttributes(path);
   if((attrs&FileAttributes.ReparsePoint)!=0)throw new IOException("Choose the original item instead of a linked folder.");
   if((attrs&FileAttributes.Hidden)!=0){errors.Add(Path.GetFileName(path)+": already hidden.");continue;}
   // Persist recovery information before changing the file; never move or delete it.
   bool added=!hiddenPaths.Exists(p=>string.Equals(p,path,StringComparison.OrdinalIgnoreCase));
   if(added){hiddenPaths.Add(path);try{SaveHiddenFiles();}catch{hiddenPaths.Remove(path);throw;}}
   try{File.SetAttributes(path,attrs|FileAttributes.Hidden);}catch{if(added){hiddenPaths.Remove(path);SaveHiddenFiles();}throw;}
   count++;
  }catch(Exception e){errors.Add(Path.GetFileName(path)+": "+e.Message);}
  BrowseFolder(currentFolder);RefreshHiddenFiles();
  fileStatus.Text=count+" hidden. Use Hidden files to unhide."+(errors.Count>0?" "+errors.Count+" could not be hidden.":"");
  if(errors.Count>0)MessageBox.Show(this,string.Join(Environment.NewLine,errors.ToArray()),"Some items were not hidden",MessageBoxButtons.OK,MessageBoxIcon.Information);
 }
 void RefreshHiddenFiles(){
  hiddenFileList.BeginUpdate();hiddenFileList.Items.Clear();
  foreach(string path in hiddenPaths){string status;try{status=HasHiddenAttribute(path)?"Hidden":"Visible";}catch(FileNotFoundException){status="Not found";}catch(DirectoryNotFoundException){status="Not found";}catch{status="Unavailable";}
   var item=new ListViewItem(Path.GetFileName(path));item.SubItems.Add(path);item.SubItems.Add(status);item.Tag=path;hiddenFileList.Items.Add(item);
  }hiddenFileList.EndUpdate();hiddenFileStatus.Text=hiddenFileReadError.Length>0?hiddenFileReadError:hiddenPaths.Count+" tracked hidden items";
 }
 void UnhideFiles(List<string> paths){
  int count=0;var errors=new List<string>();
  foreach(string path in paths)try{
   // Clear only Hidden; preserve read-only, archive, and all other file attributes.
   FileAttributes attrs=File.GetAttributes(path);File.SetAttributes(path,attrs&~FileAttributes.Hidden);
   hiddenPaths.Remove(path);try{SaveHiddenFiles();}catch{hiddenPaths.Add(path);throw;}count++;
  }catch(Exception e){errors.Add(Path.GetFileName(path)+": "+e.Message);}
  RefreshHiddenFiles();if(Directory.Exists(currentFolder))BrowseFolder(currentFolder);
  hiddenFileStatus.Text=count+" unhidden."+(errors.Count>0?" "+errors.Count+" could not be unhidden; their records were kept.":"");
  if(errors.Count>0)MessageBox.Show(this,string.Join(Environment.NewLine,errors.ToArray()),"Some items could not be unhidden",MessageBoxButtons.OK,MessageBoxIcon.Information);
 }
}
