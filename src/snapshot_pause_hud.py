"""Read-only pause/HUD candidate counters using fresh launcher identities.

python snapshot_pause_hud.py --directory outputs/local-checkpoint-...
Read results only through coop_summary.py --directory <printed JSON path>.
"""
import argparse
import json
import struct
import uuid
from pathlib import Path
from coop_runtime_session import read_targets,open_reader
from pe_image_readonly import PE32


def capture(directory):
    rows=[]
    for filename in ('host-session.json','guest-session.json'):
        for target in read_targets(directory/filename):
            if target['role']=='SERVER':continue
            reader,_=open_reader(target)
            try:
                image=PE32(Path(target['path']).read_bytes())
                row=dict(role=target['role'],pid=target['pid'])
                for name,fields in (('.pausest',('active','entity','engaged','restored','skipped_cutscene','skipped_ai')),
                                     ('.hudstat',('policy_applied','timer_suppressed','autolog_panel_suppressed'))):
                    sec=next((s for s in image.sections if s['name']==name),None)
                    if sec:
                        values=struct.unpack('<%dI'%len(fields),reader.read(image.base+sec['rva'],len(fields)*4))
                        row[name]=dict(zip(fields,values))
                rows.append(row)
            finally:reader.close()
    return dict(session=str(directory),clients=rows,gameplay_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True,type=Path)
    args=p.parse_args()
    result=capture(args.directory)
    out=Path(__file__).resolve().parent/'outputs'/('pause-hud-state-'+uuid.uuid4().hex[:12]+'.json')
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(out)
