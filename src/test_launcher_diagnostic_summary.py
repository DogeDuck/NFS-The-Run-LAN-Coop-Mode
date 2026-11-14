"""Bounded support summaries of synthetic opt-in logs, no real session logs read."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import coop_summary as summary

class LauncherSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-log-summary-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name)
    def write(self,name,rows):
        (self.directory/name).write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf-8')
    def test_rotated_samples_and_native_exception_exit_are_summarized(self):
        self.write('events.1.jsonl',[dict(Type='sample',Role='Guest',Nickname='Alice',Version='1.0-TEST',WorkingSetBytes=1024**3,PeerStatus='compatible')])
        self.write('events.jsonl',[dict(Type='session-ended',Role='Guest',Nickname='Alice',Version='1.0-TEST',ExitCode=-1073741819)])
        out='\n'.join(summary.launcher_diagnostics(self.directory))
        self.assertIn('Samples=1',out);self.assertIn('1024.0 MiB',out);self.assertIn('0xC0000005',out)
        self.assertIn('does not establish the cause',out);self.assertIn('No native race',out)
    def test_absent_logs_and_missing_end_never_imply_gameplay_success(self):
        self.assertIn('Logging may be disabled','\n'.join(summary.launcher_diagnostics(self.directory)))
        self.write('events.jsonl',[dict(Type='sample',PeerStatus='unavailable')])
        out='\n'.join(summary.launcher_diagnostics(self.directory))
        self.assertIn('not proof of a crash',out);self.assertNotIn('VERDICT: OK',out)
    def test_invalid_rows_and_oversize_file_are_bounded(self):
        (self.directory/'events.2.jsonl').write_bytes(b'x'*(3*1024*1024+1))
        (self.directory/'events.jsonl').write_text('not-json\n[]\n'+json.dumps(dict(Type='sample',WorkingSetBytes=True))+'\n')
        out='\n'.join(summary.launcher_diagnostics(self.directory))
        self.assertIn('invalid rows=2, oversized files=1',out);self.assertNotIn('MiB',out)
    def test_cli_accepts_an_arbitrary_per_player_folder(self):
        result=subprocess.run([sys.executable,str(Path(summary.__file__)),'--launcher-logs',str(self.directory)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('no readable samples',result.stdout)

if __name__=='__main__':unittest.main()
