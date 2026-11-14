"""Separate native gas-entry gate for exact0.7.6 headless server; never installs."""
import hashlib
from pe_adapter import append_adapter
from pe_image_readonly import PE32
import gas_entry_guard_adapter as a

BASE='b4dfa348819bcac31872095e6959aa9baf07c143e8543ca8e32bb4cee40ebd0c'
RACESTART='bcdafbf8db104fb070e093e147e9e3d440daef15f4499c3a2037313a14bc40aa'
R2='f2e5a72ccb5d781833e58395715c08e1b7a400c5700e0177b5861ad66f688173'


def build(base, expected=BASE):
    if expected not in (BASE,RACESTART,R2) or hashlib.sha256(base).hexdigest()!=expected:
        raise ValueError('Exact frozen supported server required')
    original=PE32(base)
    if original.read(a.SITE,5)!=a.call_patch(a.TARGET):raise ValueError('OnEnter dispatch CALL differs')
    if original.read(0x1307952,5)!=bytes.fromhex('686cad35fb'):
        raise ValueError('OnEnter PlayerEvent construction differs')
    if original.read(0x1306BD0,9)!=bytes.fromhex('83ec10568bf18b4614'):
        raise ValueError('Native trigger data layout differs')
    if original.read(0x13E1B15,6)!=bytes.fromhex('c706a09b5b02'):
        raise ValueError('SimpleAreaTrigger constructor type differs')
    data,layout,code,_=append_adapter(base,a.make_code,b'.gasgate',b'.gasgst')
    offset=PE32(data).offset(a.SITE,5)
    data[offset:offset+5]=a.call_patch(layout['adapter'])
    return bytes(data),dict(**layout,site=hex(a.SITE),target=hex(a.TARGET),
        gas_data_guid=str(a.GAS_GUID),installed=False,published=False,gameplay_verified=False,
        server_only=True,changes_assets=False,changes_world_collision=False,
        scope='Suppress only gas-prefab SimpleAreaTrigger OnEnter in active driving Story; preserve OOC/intro',
        limitation='Runtime template GUID/type match and actual no-entry need a joint game test.')
