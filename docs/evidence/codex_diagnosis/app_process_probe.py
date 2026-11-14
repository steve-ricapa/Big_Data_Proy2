"""Read only allowlisted environment/config metadata from Codex processes."""
import ctypes
import json
import os
import subprocess
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path

kernel=ctypes.WinDLL('kernel32',use_last_error=True)
nt=ctypes.WinDLL('ntdll')
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
kernel.OpenProcess.restype=wintypes.HANDLE
kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
kernel.ReadProcessMemory.restype=wintypes.BOOL
kernel.CloseHandle.argtypes=[wintypes.HANDLE]
class Basic(ctypes.Structure):
 _fields_=[('reserved1',ctypes.c_void_p),('peb',ctypes.c_void_p),('reserved2',ctypes.c_void_p*2),('pid',ctypes.c_void_p),('reserved3',ctypes.c_void_p)]
nt.NtQueryInformationProcess.argtypes=[wintypes.HANDLE,wintypes.ULONG,ctypes.c_void_p,wintypes.ULONG,ctypes.c_void_p]
nt.NtQueryInformationProcess.restype=wintypes.LONG

def environment(pid):
 handle=kernel.OpenProcess(0x410,False,pid)
 if not handle:return {'inspection':'access_denied'}
 try:
  def read(address,size):
   data=ctypes.create_string_buffer(size);count=ctypes.c_size_t()
   assert kernel.ReadProcessMemory(handle,address,data,size,ctypes.byref(count)), 'read_denied'
   return data.raw[:count.value]
  info=Basic()
  assert nt.NtQueryInformationProcess(handle,0,ctypes.byref(info),ctypes.sizeof(info),None)==0
  params=int.from_bytes(read(info.peb+0x20,8),'little')
  block=int.from_bytes(read(params+0x80,8),'little')
  entries=[];data=b''
  for offset in range(0,131072,512):
   data+=read(block+offset,512)
   text=data.decode('utf-16-le',errors='replace')
   if '\0\0' in text:
    entries=text.split('\0\0',1)[0].split('\0');break
  assert entries,'environment_terminator_not_found'
  values=dict(s.split('=',1) for s in entries if '=' in s and not s.startswith('='))
  return {'inspection':'read_only_allowlist','CODEX_HOME':values.get('CODEX_HOME'),'HOME':values.get('HOME'),'USERPROFILE':values.get('USERPROFILE'),'LOCALAPPDATA':values.get('LOCALAPPDATA')}
 except (AssertionError,OSError):return {'inspection':'unavailable'}
 finally:kernel.CloseHandle(handle)

command='Get-CimInstance Win32_Process | Where-Object { $_.Name -match "(?i)^(codex|chatgpt)\\.exe$" } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3'
p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=30,check=True)
processes=json.loads(p.stdout)
out={'at':datetime.now(UTC).isoformat(),'processes':[]}
shell=ctypes.WinDLL('shell32')
shell.CommandLineToArgvW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_int)]
shell.CommandLineToArgvW.restype=ctypes.POINTER(wintypes.LPWSTR)
kernel.LocalFree.argtypes=[ctypes.c_void_p]
for proc in processes:
 if proc['Name'].lower()!='codex.exe' and proc['ParentProcessId']!=16532 and proc['ProcessId']!=16532:continue
 raw=proc.get('CommandLine') or ''
 row={k:proc.get(k) for k in ('ProcessId','ParentProcessId','Name','ExecutablePath')}
 if proc['Name'].lower()=='codex.exe' or proc['ProcessId']==16532:
  row['environment']=environment(proc['ProcessId'])
  count=ctypes.c_int();argv=shell.CommandLineToArgvW(raw,ctypes.byref(count))
  args=[argv[i] for i in range(count.value)] if argv else []
  if argv:kernel.LocalFree(argv)
  row['app_server']='app-server' in args
  row['config_override_keys']=[]
  row['safe_overrides']={}
  for i,arg in enumerate(args[:-1]):
   if arg in ('-c','--config'):
    value=args[i+1];key=value.split('=',1)[0]
    row['config_override_keys'].append(key)
    if key in ('mcp_oauth_credentials_store','mcp_servers.big_data_ii_-_threat_intelligence.enabled','mcp_servers.big_data_ii_-_threat_intelligence.environment_id','mcp_servers.big_data_ii_-_threat_intelligence.oauth.client_id'):
     row['safe_overrides'][key]=value.split('=',1)[1]
   if arg=='--remote':
    address=args[i+1]
    row['remote_transport']=address.split(':',1)[0]
    row['remote_loopback']=('127.0.0.1' in address or 'localhost' in address)
 out['processes'].append(row)
out['self_environment_check']=(environment(os.getpid()).get('USERPROFILE')==os.environ.get('USERPROFILE'))
Path(__file__).with_name('app_process.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
