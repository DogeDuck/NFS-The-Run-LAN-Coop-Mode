"""Build an isolated, not gameplay-verified native multiplayer HUD candidate."""
import struct
import coop_hud_adapter as a
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import file_offset,digest


def build(base):
    im=PE32(base)
    for site,expected in ((a.POLICY_SITE,a.POLICY_BYTES),(a.VISIBILITY_SITE,a.VISIBILITY_BYTES),
                          (0x915899,bytes.fromhex('55558bcee8'))):
        if im.read(site,len(expected))!=expected:raise ValueError('HUD native contract changed at '+hex(site))
    # Reflection descriptors: string pointer, flags, numeric enum value.
    for address,value,name in ((0x2B21724,6,b'HUDWidgetType_RaceTimer'),
                               (0x2B2173C,8,b'HUDWidgetType_SplitTimes'),
                               (0x2B216E8,1,b'HUDWidgetType_Leaderboard'),
                               (0x2B0648C,1,b'GameModeCopy_CareerMode'),
                               (0x2B06498,2,b'GameModeCopy_StoryMode')):
        ptr,_,actual=struct.unpack('<3I',im.read(address,12))
        if actual!=value or im.read(ptr,len(name)+1)!=name+b'\0':raise ValueError('HUD enum contract changed')
    patched,layout,code,_=append_adapter(base,a.make_code,b'.coophud',b'.hudstat')
    for site,target,expected in ((a.POLICY_SITE,layout['adapter'],a.POLICY_BYTES),
                                 (a.VISIBILITY_SITE,layout['adapter']+a.VISIBILITY_OFFSET,a.VISIBILITY_BYTES)):
        off=file_offset(patched,site)
        patched[off:off+len(expected)]=b'\xe9'+struct.pack('<i',target-site-5)+b'\x90'*(len(expected)-5)
    return bytes(patched),code,dict(sha256=digest(patched),layout=layout,
        native_leaderboard=True,hide_story_timer=True,hide_autolog_stage_leader=True,
        race_data_modified=False,gameplay_verified=False,
        limitations='Candidate only. Native Career leaderboard may require additional data initialization in Story LAN; no teammate-only filter or invented seconds gap.')
