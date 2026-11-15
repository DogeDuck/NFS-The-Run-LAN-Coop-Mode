using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;
[assembly: AssemblyTitle("The Run Co-op Setup")]
[assembly: AssemblyVersion("0.7.9.0")]
internal static class SetupBootstrap {
 const string ExpectedZip="PAYLOAD_SHA256";
 [STAThread] static int Main(string[] args) {
  try {
   string destination;
   bool extractOnly=args.Length==2 && args[0]=="--extract-only";
   if(args.Length!=0 && !extractOnly)throw new Exception("Unsupported argument / Unbekannter Parameter");
   if(extractOnly)destination=Path.GetFullPath(args[1]);
   else destination=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"TheRunStoryCoop","SetupCache",Guid.NewGuid().ToString("N"));
   if(Directory.Exists(destination) && Directory.GetFileSystemEntries(destination).Length>0)throw new Exception("Extraction folder is not empty / Zielordner ist nicht leer");
   Directory.CreateDirectory(destination);
   byte[] bytes;
   using(Stream input=Assembly.GetExecutingAssembly().GetManifestResourceStream("TheRunPayload.zip"))
   using(MemoryStream memory=new MemoryStream()){if(input==null)throw new Exception("Setup payload missing");input.CopyTo(memory);bytes=memory.ToArray();}
   using(SHA256 hash=SHA256.Create()){string actual=BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();if(actual!=ExpectedZip)throw new Exception("Setup checksum mismatch / Setup-Pruefsumme falsch");}
   string prefix=destination.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
   HashSet<string> seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   using(MemoryStream input=new MemoryStream(bytes))
   using(ZipArchive zip=new ZipArchive(input,ZipArchiveMode.Read)) {
    if(zip.Entries.Count>6000)throw new Exception("Setup file bound exceeded");
    long total=0;
    foreach(ZipArchiveEntry entry in zip.Entries){
     string name=entry.FullName.Replace('/',Path.DirectorySeparatorChar);
     string target=Path.GetFullPath(Path.Combine(destination,name));
     if(Path.IsPathRooted(name)||name.Contains(":")||!target.StartsWith(prefix,StringComparison.OrdinalIgnoreCase)||!seen.Add(target))throw new Exception("Unsafe setup path");
     if(((entry.ExternalAttributes>>16)&0xF000)==0xA000||(entry.ExternalAttributes&0x400)!=0)throw new Exception("Setup links unsupported");
     total+=entry.Length;if(total>419430400)throw new Exception("Setup size bound exceeded");
    }
    foreach(ZipArchiveEntry entry in zip.Entries){
     string target=Path.GetFullPath(Path.Combine(destination,entry.FullName.Replace('/',Path.DirectorySeparatorChar)));
     if(entry.Name.Length==0){Directory.CreateDirectory(target);continue;}
     Directory.CreateDirectory(Path.GetDirectoryName(target));
     using(Stream source=entry.Open())using(FileStream output=new FileStream(target,FileMode.CreateNew,FileAccess.Write)){source.CopyTo(output);}
    }
   }
   if(extractOnly)return 0;
   string script=Path.Combine(destination,"TheRun-Coop-v0.7.9-TEST","Setup-Coop.ps1");
   if(!File.Exists(script))throw new Exception("Setup UI missing");
   ProcessStartInfo info=new ProcessStartInfo();
   info.FileName=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows),"System32","WindowsPowerShell","v1.0","powershell.exe");
   info.Arguments="-STA -NoProfile -ExecutionPolicy Bypass -File \""+script+"\"";
   info.WorkingDirectory=Path.GetDirectoryName(script);info.UseShellExecute=false;info.CreateNoWindow=true;
   Process.Start(info);
   return 0;
  }catch(Exception error){MessageBox.Show(error.Message,"The Run Co-op Setup",MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
 }
}
