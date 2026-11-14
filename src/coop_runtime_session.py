"""Resolve current launcher sessions for local or Radmin diagnosis. No auto launch."""
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
from coop_diagnostics import Reader

CLIENT_NAME='Need For Speed The Run.exe'
SERVER_NAME='NFSTR_Server.exe'
QTE_DELTA_BUILD='1BCF0628DB85D4757DE22219DF395034157FE440D2BE64053434F883CD33BED1'
CLIENT_BUILDS={'C3FBA53C787F6B4EDF97B142E2477F3FEC4A8BF9FF0C6ADACDF7BEADD17CC0D6','7FD4BFB845DEB7C2F78F1220706599C52ADE487E3303A42AE4818EEE31A94269','42746E48E5E20FC3EE96C54F30EB0B4D6070D48A966EB9483386AA18DB4C309E','95BA75BB168B2FFC38C4539E2287D8BE31DCC55D2001D53C7C7A60696C839F14','2993294546FFE5E70DB4FF2BBD58680A096C7D39C08412D0FA3C556725DC3CEF','C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6',
               # 07.11. HUD pause-state AI + native Career HUD, offline-tested candidate.
               '4AFC9B078F7C70044AB48C05CC3327DCBFB05EF489AAB190C5A6640E8043AD29',
               # v0.6 + client-only native unload acknowledgement (offline candidate, not installed).
               '8140947E9B11CDFA4CAC5D3C7F05820A96246F447399ED6ADC6187355910D5C6',
               '2CB4570C34E46CC74CCDED44F8F38338C12A0EDFBB33A74572B72FC6E11AD249',
               # v0.6 client + pause-AI draft (outputs/TheRun-Coop-v0.6-COOP-CANDIDATE), read-only diagnostics
               '17E06079F897AAF4CC904C1B5E0FBA4E37D5BD94200A4EB51D4D897AA753738B',
               # same without the entity+D0 guard (outputs/TheRun-Coop-v0.6-COOP-CANDIDATE-NOGUARD)
               '25167583C71EC9AD530A3636E4B3607A4707EF7105A4CD5DAABE65AC295F8B9B'}
SERVER_BUILDS={'B5D06A6971C95F4A0BA23C1B5840817910865F413477B447A1E13A98D6D8F441','C9AB0D36FF35D9CF2548BDC73A94D911CC2065A921FA4A4AFAC86AD2E593A988','4AFB76C21D08439778DBA038AD787618F752AA3C639A18A07A5B1672C0263C9D',
               'DCFAFC833016BAADE51F556C82963BA8C015406ADC69BEA0006919AD7DD68695',
               '79368D76F6967918C2AE0208757546AA5A0E197B8EE9BFDB631ED809F15AC79E',
               '22F1604CC40643DBCB18154CDA3DA627A63F0B34A4DFDFD7631AD99C9A81B768',
               '76F2D6DDDBBEAE3C6FDA85644C4D9D65ED7551AB6542AD4D08750EA4F2C04A92',
               '2BBD8E66B7E5219CF72C7CCCA06404AA2C36712F2B58E4CFEFCAA53C1082066C',
               # v0.6 + second-human slot reservation (outputs/slot-reservation-candidate-20261104), read-only diagnostics
               'AEAF9C120B02A158CD3F52554FBFA1F2F0F18507DA43D9C4AA00225C845249FF',
               # + battle team finish draft (outputs/TheRun-Coop-v0.6-SLOT-BATTLE-CANDIDATE), read-only diagnostics
               'B912B57BF013DC6AC37C2BC0DAE8367496776ED5429F7AFCE6B319015AE8512C',
               # v0.6 + gas station ack timeout draft (outputs/TheRun-Coop-v0.6-GAS-CANDIDATE), read-only diagnostics
               '9E0137A9F329F4FE02A16DC9AD927B3CFFB70C909C86856222C13042143FB7CB',
               # all drafts: slots + battle finish + gas ack timeout (outputs/TheRun-Coop-v0.6-ALL-CANDIDATE)
               '67B27E9381F76F641E8752DBEC587D4DF624AFAA0F6313C3EB123B0BAAA990AB'}
# v0.7.4 candidate assembled at the user's request without new tests.
# Exact hash pins only; this permits read-only diagnostics, not a gameplay claim.
CLIENT_BUILDS |= {'DF9F70693DD4167440935725174014D1643C284B05D010FE198681D4B322ACE5'}
SERVER_BUILDS |= {'E0BA314C434A38CC60BD84B75928F62AB6B9587A3FE55F08A2DC2595152047E3'}
# 10Nov: public0.7.4/0.7.5 difficulty bundle and isolated QTE local-context candidate.
CLIENT_BUILDS |= {'5F127858F1015E0E0711708173F4E5EB13439AA3FA7905878E33857962A5E7CF'}
# Isolated0.7.7 QTE failure-completion candidate; EventSync remains native.
CLIENT_BUILDS |= {'656F19DB3143AEC019176262BFF93FDEE83C28EDA5F1D8CA85C750963DF641D6'}
CLIENT_BUILDS |= {'1B8EA7B9728AC9E7285BA547F3A706071B8EB48AD61FCFEF26112E2CBDB9BF94'}
CLIENT_BUILDS |= {'56707D2D2C12D69837E9C2B24326422306A1CC0528DE999F69FF9E1FDBC3B529'}
SERVER_BUILDS |= {'B4DFA348819BCAC31872095E6959AA9BAF07C143E8543CA8E32BB4CEE40EBD0C'}
SERVER_BUILDS |= {'9FCB605EC14E8EC6D5E6E230F3CD2DB6EB2A8B672DD4218D5AB7B725BC4F9A27'}
SERVER_BUILDS |= {'359E9F2AA6C0ED64832D610FDBAEE50242C55205BD878AC3148ACF5FDDFED61C'}
DOTNET_FILETIME_EPOCH=504911232000000000
SERVER_BUILDS |= {'923259C69C15DF8F150F23382C131B03C4BB1133BFBDB63B88282A262322198D'}

def default_session_path():
    directory=os.environ.get('LOCALAPPDATA')
    if not directory:raise ValueError('LOCALAPPDATA missing; use --session')
    return Path(directory)/'TheRunStoryCoop/active-session.json'

def select_targets(session):
    if session.get('Status')!='running':raise ValueError('Launcher session is not running')
    role=session.get('Role')
    if role not in ('Host','Guest'):raise ValueError('Unknown session role')
    game=PureWindowsPath(session['GameDirectory'])
    if not game.is_absolute() or any(p.upper()=='THERUNBACKUP' for p in game.parts):
        raise ValueError('Invalid game directory')
    result=[]
    specs=[('Client','HOST' if role=='Host' else 'GAST',CLIENT_NAME)]
    if role=='Host':specs.append(('Server','SERVER',SERVER_NAME))
    for key,label,name in specs:
        record=session.get(key)
        if not isinstance(record,dict):raise ValueError(f'Missing {key} process record')
        if type(record.get('Id')) is not int or record['Id']<=0:raise ValueError('Invalid PID')
        if type(record.get('StartTicks')) is not int or record['StartTicks']<=DOTNET_FILETIME_EPOCH:
            raise ValueError('Missing process creation time')
        expected=game/name
        if PureWindowsPath(record.get('Path',''))!=expected:raise ValueError('Process path does not match session game directory')
        result.append(dict(role=label,pid=record['Id'],path=str(expected),start_ticks=record['StartTicks']))
    if len({row['pid'] for row in result})!=len(result):raise ValueError('Duplicate PID')
    return result

def read_targets(path=None):
    return select_targets(json.loads((path or default_session_path()).read_text(encoding='utf-8-sig')))

def open_reader(target,extra_builds=frozenset()):
    """extra_builds: optional caller-specific hashes (e.g. an offline candidate)."""
    allowed=(SERVER_BUILDS if target['role']=='SERVER' else CLIENT_BUILDS|{QTE_DELTA_BUILD})|{h.upper() for h in extra_builds}
    digest=hashlib.sha256(Path(target['path']).read_bytes()).hexdigest().upper()
    if digest not in allowed:raise ValueError('Unsupported executable build')
    reader=Reader(target['pid'],Path(target['path']))
    try:
        if reader.creation_time()+DOTNET_FILETIME_EPOCH!=target['start_ticks']:
            raise ValueError('PID was reused or process creation time changed')
        return reader,digest
    except BaseException:
        reader.close();raise
