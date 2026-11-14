"""Launcher version/lease protocol and opt-in log bounds. No game processes."""
import base64,json,os,socket,subprocess,threading,tempfile,unittest
from pathlib import Path
import test_launcher_bilingual as launcher

class SessionToolsTests(unittest.TestCase):
    ps=launcher.LauncherBilingualTests.ps
    literal=staticmethod(launcher.LauncherBilingualTests.literal)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-session-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.environment=dict(os.environ,LOCALAPPDATA=str(self.directory))
    def call(self,code,success=True):
        return self.ps("$ErrorActionPreference='Stop';. "+self.literal(launcher.TOOLS/'Coop-SessionTools.ps1')+';'+code,success=success)
    def state(self):
        return "$s=New-CoopPeerState @{Version='1.0-TEST';Compatibility=('a'*64)} 'HostOne' 4 3;"
    def test_two_to_four_names_and_capacity_without_player_id_assumptions(self):
        for count in (2,3,4):
            code=self.state()+f'$s.MaxPlayers={count};'
            code+="$results=@();foreach($n in 1..4){$r=Invoke-CoopPeerRequest $s @{Protocol=1;Kind='hello';Nickname=('Player'+$n);Version='1.0-TEST';Compatibility=('a'*64)} ('127.0.0.'+$n);$results+=$r.Status};@{Status=$results;Peers=$s.Peers.Count}|ConvertTo-Json"
            result=json.loads(self.call(code).stdout)
            self.assertEqual(result['Peers'],count-1)
            self.assertEqual(result['Status'][:count-1],['compatible']*(count-1))
            self.assertEqual(result['Status'][count-1:],['full']*(5-count))
    def test_mismatch_probe_and_duplicate_name_never_register_fake_players(self):
        code=self.state()+"$a=Invoke-CoopPeerRequest $s @{Protocol=1;Kind='probe';Nickname='Guest';Compatibility=('a'*64)} '127.0.0.1';$b=Invoke-CoopPeerRequest $s @{Protocol=1;Kind='hello';Nickname='Guest';Compatibility=('b'*64)} '127.0.0.1';$c=Invoke-CoopPeerRequest $s @{Protocol=1;Kind='hello';Nickname='HostOne';Compatibility=('a'*64)} '127.0.0.1';@{A=$a.Status;B=$b.Status;C=$c.Status;Peers=$s.Peers.Count}|ConvertTo-Json"
        self.assertEqual(json.loads(self.call(code).stdout),dict(A='compatible',B='mismatch',C='full',Peers=0))
    def test_expired_guest_is_removed_and_unknown_request_rejected(self):
        code=self.state()+"$time=[datetime]'2026-11-14T20:00:00Z';[void](Invoke-CoopPeerRequest $s @{Protocol=1;Kind='hello';Nickname='Guest';Compatibility=('a'*64)} '127.0.0.2' $time);$r=Invoke-CoopPeerRequest $s @{Protocol=1;Kind='exec';Nickname='Guest';Compatibility=('a'*64)} '127.0.0.2' $time.AddSeconds(21);@{Peers=$s.Peers.Count;Status=$r.Status}|ConvertTo-Json"
        self.assertEqual(json.loads(self.call(code).stdout),dict(Peers=0,Status='invalid'))
    def test_real_tcp_query_matches_package_and_mismatch_blocks(self):
        manifest=dict(version='1.0-TEST',client_sha256='a'*64,server_sha256='b'*64)
        (self.directory/'package-manifest.json').write_text(json.dumps(manifest))
        compatibility=json.loads(self.call('Get-CoopCompatibility '+self.literal(self.directory)+'|ConvertTo-Json').stdout)
        for mismatch in (False,True):
            srv=socket.socket();srv.bind(('127.0.0.1',0));srv.listen();port=srv.getsockname()[1];requests=[]
            def serve():
                try:
                    with srv.accept()[0] as client:
                        raw=b''
                        while not raw.endswith(b'\n'):raw+=client.recv(1024)
                        requests.append(json.loads(raw))
                        answer=dict(Protocol=1,Status='mismatch' if mismatch else 'compatible',Version='2.0-TEST' if mismatch else '1.0-TEST',Compatibility='f'*64 if mismatch else compatibility['Compatibility'])
                        client.sendall(json.dumps(answer).encode()+b'\n')
                finally:srv.close()
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            r=self.call('Test-CoopPeerVersion '+self.literal(self.directory)+f" '127.0.0.1' 'Guest' {port}|ConvertTo-Json",success=not mismatch)
            thread.join(3);self.assertFalse(thread.is_alive());self.assertEqual(requests[0]['Kind'],'probe')
    def test_diagnostic_rotation_and_message_limit(self):
        folder=self.directory/'logs'
        self.call("1..20|ForEach-Object {Write-CoopDiagnosticEvent "+self.literal(folder)+" @{At='now';Type='sample';Payload=('x'*100)} 200}")
        self.assertLessEqual(len(list(folder.iterdir())),3)
        self.assertLess(sum(p.stat().st_size for p in folder.iterdir()),1200)
        self.call("$s=[IO.MemoryStream]::new([Text.Encoding]::UTF8.GetBytes(('x'*20)+\"`n\"));Read-CoopPeerLine $s 8",success=False)
    def test_real_powershell_host_listener_handles_bad_then_valid_client(self):
        # Exercise the actual host receive loop, not a Python substitute for it.
        probe=socket.socket();probe.bind(('127.0.0.1',0));port=probe.getsockname()[1];probe.close()
        stop=self.directory/'stop'
        code="$ErrorActionPreference='Stop';. "+self.literal(launcher.TOOLS/'Coop-SessionTools.ps1')+';'+self.state()
        code+=f"$l=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,{port});$l.Start();try{{[Console]::WriteLine('READY');$end=[datetime]::UtcNow.AddSeconds(12);while([datetime]::UtcNow -lt $end -and !(Test-Path -LiteralPath "+self.literal(stop)+")){Receive-CoopPeerRequests $l $s;Start-Sleep -Milliseconds 10};@{Peers=$s.Peers.Count}|ConvertTo-Json -Compress}finally{$l.Stop()}"
        encoded=base64.b64encode(code.encode('utf-16-le')).decode('ascii')
        process=subprocess.Popen([str(launcher.PWSH),'-NoProfile','-EncodedCommand',encoded],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf-8',env=self.environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            self.assertEqual(process.stdout.readline().strip(),'READY')
            # A malformed/oversize client must be closed without killing the broker.
            with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
                client.sendall(b'x'*4100+b'\n')
                try:self.assertEqual(client.recv(1),b'')
                except ConnectionResetError:pass  # Windows closes unread oversize data with RST.
            with socket.create_connection(('127.0.0.1',port),timeout=3) as client:
                client.sendall(json.dumps(dict(Protocol=1,Kind='hello',Nickname='GuestTwo',Version='1.0-TEST',Compatibility='a'*64)).encode()+b'\n')
                data=b''
                while not data.endswith(b'\n'):data+=client.recv(4096)
                reply=json.loads(data)
                self.assertEqual(reply['Status'],'compatible')
                self.assertEqual([p['Nickname'] for p in reply['Players']],['HostOne','GuestTwo'])
            stop.touch();out,err=process.communicate(timeout=5)
            self.assertEqual(process.returncode,0,err)
            self.assertEqual(json.loads(out),{'Peers':1})
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=5)
    def test_host_preflight_rejects_occupied_control_port(self):
        with socket.socket() as listener:
            listener.bind(('0.0.0.0',0));listener.listen();port=listener.getsockname()[1]
            self.call(f'Assert-CoopPeerPortAvailable {port}',success=False)
        self.call(f'Assert-CoopPeerPortAvailable {port}')

if __name__=='__main__':unittest.main()
