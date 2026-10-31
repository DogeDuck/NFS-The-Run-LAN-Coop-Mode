param([int]$GameProcessId,[string]$GameDirectory,[string]$LogPath,[switch]$CompileOnly)
$ErrorActionPreference='Stop'
if(-not ('NFSTRCoopGarageSession' -as [type])){
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
public sealed class NFSTRCoopGarageSession : IDisposable {
 [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint a,bool b,int p);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool ReadProcessMemory(IntPtr h,IntPtr a,byte[] b,UIntPtr n,out UIntPtr got);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool WriteProcessMemory(IntPtr h,IntPtr a,byte[] b,UIntPtr n,out UIntPtr got);
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern bool QueryFullProcessImageName(IntPtr h,uint f,StringBuilder s,ref uint n);
 [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr h,out uint e);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 IntPtr handle; uint lastArray; uint lastCount;
 public NFSTRCoopGarageSession(int pid,string expected) {
  handle=OpenProcess(0x438,false,pid);
  if(handle==IntPtr.Zero)throw new Win32Exception();
  try {
   var text=new StringBuilder(32768); uint n=32768;
   if(!QueryFullProcessImageName(handle,0,text,ref n) || !String.Equals(text.ToString(),expected,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Game process path mismatch");
  } catch {Dispose();throw;}
 }
 byte[] Read(uint address,int size) {
  byte[] b=new byte[size];UIntPtr got;
  if(!ReadProcessMemory(handle,new IntPtr((long)address),b,(UIntPtr)size,out got) || got.ToUInt64()!=(ulong)size)throw new Win32Exception();
  return b;
 }
 uint U(uint address) {return BitConverter.ToUInt32(Read(address,4),0);}
 public bool Alive {get {uint exit;return GetExitCodeProcess(handle,out exit)&&exit==259;}}
 public int Tick() {
  uint online=U(0x2888F7C);
  if(online==0 || Read(online+8,1)[0]!=0 || U(online+0xA4)!=3)return 0;
  uint root=U(0x2880420); if(root==0)return 0;
  uint data=U(root+0x14);if(data==0)return 0;
  uint catalog=U(data+0x34);if(catalog==0)return 0;
  uint array=U(catalog+0x18);if(array<4)return 0;
  uint count=U(array-4);if(count==0 || count>1024)return 0;
  if(array==lastArray && count==lastCount)return 0;
  int changed=0;
  for(uint i=0;i<count;i++){
   uint car=U(array+i*4);uint getter=U(U(car));byte[] code=Read(getter,6);
   if(code[0]!=0xB8 || BitConverter.ToUInt32(code,1)!=0x2AD6E90 || code[5]!=0xC3)throw new InvalidOperationException("GarageCar identity mismatch");
   byte[] flags=Read(car+0x18,2);
   if(flags[0]>1 || flags[1]>1)throw new InvalidOperationException("Unexpected garage flags");
   if(flags[0]==1 && flags[1]==1)continue;
   UIntPtr wrote;
   if(!WriteProcessMemory(handle,new IntPtr((long)(car+0x18)),new byte[]{1,1},(UIntPtr)2,out wrote) || wrote.ToUInt64()!=2)throw new Win32Exception();
   byte[] check=Read(car+0x18,2);
   if(check[0]!=1 || check[1]!=1)throw new InvalidOperationException("Garage flag readback mismatch");
   changed++;
  }
  lastArray=array;lastCount=count;return changed;
 }
 public void Dispose(){if(handle!=IntPtr.Zero){CloseHandle(handle);handle=IntPtr.Zero;}}
}
'@
}
if($CompileOnly){Write-Output 'Garage helper compiled; no process opened.';return}
if($GameProcessId -le 0 -or !$GameDirectory){throw 'GameProcessId and GameDirectory required'}
$exe=Join-Path $GameDirectory 'Need For Speed The Run.exe'
if((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne '2CB4570C34E46CC74CCDED44F8F38338C12A0EDFBB33A74572B72FC6E11AD249'){throw 'Unsupported garage helper build'}
$session=[NFSTRCoopGarageSession]::new($GameProcessId,$exe)
try {
 while($session.Alive){
  try {
   $changed=$session.Tick()
   if($changed -gt 0 -and $LogPath){Add-Content -LiteralPath $LogPath -Value ((Get-Date).ToString('o')+': session-only GarageCar unlocks='+$changed)}
  } catch [ComponentModel.Win32Exception] {
   # Frontend/world transitions may temporarily leave root pointers unavailable.
  }
  Start-Sleep -Seconds 2
 }
} finally {$session.Dispose()}
