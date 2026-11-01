"""Build v0.5 from your own verified v0.4 server; no game binary is bundled."""
from pathlib import Path
import argparse,json
from patch_story_ai_gate import build as ai
from patch_story_start_spawn import build as spawn
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('original',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
if a.output.exists():raise ValueError('Choose a new output file')
staged,_,ai_report=ai(a.original.read_bytes())
final,_,spawn_report=spawn(staged)
a.output.write_bytes(final)
print(json.dumps(dict(ai=ai_report,spawn=spawn_report),indent=2))
