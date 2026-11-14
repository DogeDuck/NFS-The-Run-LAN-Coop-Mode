"""Persist Claude's tested QTE mask and HUD-name adapters on exact Native-R3."""
import hashlib,struct
import qte_host_mirror_adapter as q
import nametag_names_adapter as n
import standings_names_adapter as s
import remote_lights_adapter as lights
from patch_cutscene_ai import append_sections
from pe_image_readonly import PE32
BASE='0f2f32b50f007db54aa911fa43955a3c7a95334e09ed740b0c6a26663c1bd13a'
def build(raw,expected=BASE):
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Exact verified input required')
 pins=((q.SITE,q.call_patch()),(n.SITE,n.ORIGINAL),(s.SITE,s.call_patch(s.SITE,s.TARGET)),(lights.SITE,lights.ORIGINAL))
 for at,before in pins:
  if PE32(raw).read(at,len(before))!=before:raise ValueError('Hook conflict '+hex(at))
 def factory(code,data):
  data=data or code+0x10000
  parts=[q.make_code(code,data),n.make_code(code+0x200,data+0x100),s.make_code(code+0x400,data+0x200),lights.make_code(code+0x600,data+0x300)]
  if any(len(x)>0x200 for x in parts):raise ValueError('Adapter overlap')
  return b''.join(x.ljust(0x200,b'\xcc') for x in parts)
 data=q.data_init().ljust(0x300,b'\0')+lights.data_init()
 out,code,stats=append_sections(raw,factory,data,b'.qtehud',b'.qtehudr')
 for at,value in ((q.SITE,q.call_patch(q.SITE,code)),(n.SITE,n.site_patch(code+0x200)),(s.SITE,s.call_patch(s.SITE,code+0x400)),(lights.SITE,lights.site_patch(code+0x600))):
  off=PE32(out).offset(at,len(value));out[off:off+len(value)]=value
 return bytes(out),dict(code=code,data=stats,host_qte_local_live=True,host_qte_remote_live=False,names_live=False)
