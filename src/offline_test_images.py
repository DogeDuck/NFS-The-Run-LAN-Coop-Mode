"""Version-pinned offline fixtures reconstructed from local backups, never the installed game.

Native-code tests must not silently emulate a different installed release or a solo-session EXE.
No files are written; do not bundle the user's backups in a public package.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from build_test_package import apply, reverse_apply

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT / 'release/TheRun-Coop-v0.7.6-TEST'
LAN_HASHES = {
    'client': '33853c17cb5850cc7deb9fb8e7d013815a60026be0ff3b3f6b70071cb56215e9',
    'server': '198c0d478dab01898d3dd487e1ee483c8ae0fd6bf2ed3fb03d409de5b2f1fe5e',
}
INTEGRATED_HASHES = {
    'client': 'df9f70693dd4167440935725174014d1643c284b05d010fe198681d4b322ace5',
    'server': 'b4dfa348819bcac31872095e6959aa9baf07c143e8543ca8e32bb4cee40ebd0c',
}
RESEARCH_HASHES = {
    'client': 'c9d48e500ef82efc642edf2db848a9072e56fbc114e283173d6e7e58bac634a6',
    'server': 'dcfafc833016baade51f556c82963ba8c015406adc69bea0006919ad7dd68695',
}
V05_CLIENT = '2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249'
BACKUPS = {'client': 'Need For Speed The Run.exe.lan-before-road-reset',
           'server': 'NFSTR_Server.exe.headless-original'}


def checked(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Wrong version-pinned offline test image')
    return data


@lru_cache(maxsize=8)
def image(stem, stage='lan'):
    if stem not in BACKUPS or stage not in ('lan', 'integrated', 'research', 'v05'):
        raise ValueError('Explicit client/server and known fixture stage required')
    if stage == 'lan':
        return checked((ROOT / 'backups' / BACKUPS[stem]).read_bytes(), LAN_HASHES[stem])
    if stage == 'integrated':
        patch = json.loads((RELEASE / f'patches/{stem}.json').read_text(encoding='utf-8-sig'))
        return checked(apply(image(stem, 'lan'), patch), INTEGRATED_HASHES[stem])
    if stage == 'research':
        patch = json.loads((RELEASE / f'patches/{stem}-research-upgrade.json').read_text(encoding='utf-8-sig'))
        return checked(reverse_apply(image(stem, 'integrated'), patch), RESEARCH_HASHES[stem])
    if stem != 'client':
        raise ValueError('No approved v0.5 server fixture requested by these tests')
    patch = json.loads((ROOT / 'release/TheRun-Coop-v0.3-TEST/patches/client-research-upgrade.json').read_text(encoding='utf-8-sig'))
    return checked(apply(image('client', 'research'), patch), V05_CLIENT)
