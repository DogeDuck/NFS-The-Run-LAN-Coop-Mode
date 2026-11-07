"""DRAFT client adapter, not activated: AI drives the local car while the pause menu is open (LAN only).

Native (client, statically verified, see PAUSE-KI-2026-11-04.md):
- E5F870 dispatches ClientPauseGameMessage (id 6A1B3EAB = hash of the class name); at E5FE75 it
  calls E5DA70(paused=[msg+28], 1, [msg+29]) via CALL E5FE83 (only caller for this message;
  E5FC3E/E5FC70 are streaming/sub-level pauses and stay untouched).
- The game's own AI switch (AIControlSetter handler 990540, events EnableAIControl F5CD8ECB /
  DisableAIControl DFC3863E): entity = F2E090(F26530([2888F78])) = [[2888F78]+BC]+318 (type-checked),
  then F29820(entity, enable, 0, 0). F29820 sends the request to the server (EDA970) and updates the
  local AIPlayer (entity+6C). So the AI switch stays network-consistent.
- NOT used: 69E2E0/+AEB. Its only reader 6924A0 forces brake=1/throttle=0 (a stop flag, not AI).
Adapter on CALL E5FE83 -> here, then tail-jump into native E5DA70 (pause itself unchanged):
- LAN in-game only: [[2888F7C]+8]==0 and [[2888F7C]+A4]==3,
- entity=[player+318] VT 254D220, vehicle=[entity+E4] VT 2400150,
- pause=1: skip if vehicle +A7C/+A7D (cutscene/animation owns it) or entity +D0 != 0 (F27380, AI
  state already set natively); otherwise F29820(entity,1,0,0) and remember the entity,
- pause=0: only if this adapter engaged for the same entity: F29820(entity,0,0,0).
Counters in RW state for live diagnosis. Not tested in game.
"""
import struct
from checkpoint_humans_adapter import Code

SITE, NATIVE = 0xE5FE83, 0xE5DA70
# NFSUI HUD update 900E70 reads PauseVisibilty (7344EDEB), sets +64 to
# 2 (pause visible) / 1 (hidden), then calls this UI-value destructor.
HUD_SITE, HUD_NATIVE = 0x900F68, 0xEB6850
SET_AI_CONTROL = 0xF29820
ONLINE, PLAYERS = 0x2888F7C, 0x2888F78
ENTITY_VT, VEHICLE_VT = 0x254D220, 0x2400150
# RW state
ACTIVE, ENTITY, ENGAGED, RESTORED, SKIPPED_OWNED, SKIPPED_AI = 0, 4, 8, 12, 16, 20


def absolute(c, op, address):
    c.emit(op)
    c.data += struct.pack('<I', address)


def make_code(base, stats, guard_ai_state=True, hud_state=False):
    """guard_ai_state: skip when entity+D0 != 0. Meaning of D0 is unproven (set to 1 at F3845A after a
    data copy, reset at F35780, written by F29820 on enable); if live SKIPPED_AI keeps rising, build with False."""
    c = Code(base)
    c.emit('9c60')                                   # pushfd; pushad (36 bytes)
    if hud_state:
        # Saved caller ESI is the HUD object; ESI below is reused for the vehicle.
        c.emit('8b44240485c0'); c.branch('0f84', 'native')
        c.emit('8b686483fd01'); c.branch('0f84', 'hud_valid')
        c.emit('83fd02'); c.branch('0f85', 'native')
        c.label('hud_valid')
    absolute(c, 'a1', ONLINE); c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('80780800'); c.branch('0f85', 'native')   # singleplayer -> untouched
    c.emit('83b8a400000003'); c.branch('0f85', 'native')  # not connected
    absolute(c, 'a1', PLAYERS); c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('8b80bc00000085c0'); c.branch('0f84', 'native')        # local player
    c.emit('8b801803000085c0'); c.branch('0f84', 'native')        # entity
    c.emit('8138'); c.data += struct.pack('<I', ENTITY_VT); c.branch('0f85', 'native')
    c.emit('89c7')                                                # edi = entity
    c.emit('8bb7e400000085f6'); c.branch('0f84', 'native')        # esi = vehicle
    c.emit('813e'); c.data += struct.pack('<I', VEHICLE_VT); c.branch('0f85', 'native')
    if hud_state:
        c.emit('83fd02'); c.branch('0f85', 'resume')
    else:
        c.emit('807c242800'); c.branch('0f84', 'resume')  # [esp+36+4] = paused arg
    # --- pause opened ---
    absolute(c, '833d', stats + ACTIVE); c.emit('00'); c.branch('0f85', 'native')   # already engaged
    c.emit('80be7c0a000000'); c.branch('0f85', 'owned')           # externally controlled
    c.emit('80be7d0a000000'); c.branch('0f85', 'owned')           # animation/cutscene owns car
    if guard_ai_state:
        c.emit('80bfd000000000'); c.branch('0f85', 'ai_set')      # entity+D0 != 0: leave alone
    absolute(c, '893d', stats + ENTITY)
    absolute(c, 'c705', stats + ACTIVE); c.emit('01000000')
    absolute(c, 'ff05', stats + ENGAGED)
    c.emit('6a006a006a0189f9'); c.branch('e8', SET_AI_CONTROL)    # F29820(entity,1,0,0), RET 0xC
    c.branch('e9', 'native')
    c.label('owned')
    absolute(c, 'ff05', stats + SKIPPED_OWNED); c.branch('e9', 'native')
    c.label('ai_set')
    absolute(c, 'ff05', stats + SKIPPED_AI); c.branch('e9', 'native')
    # --- pause closed ---
    c.label('resume')
    absolute(c, '833d', stats + ACTIVE); c.emit('00'); c.branch('0f84', 'native')
    absolute(c, '3b3d', stats + ENTITY); c.branch('0f85', 'drop')  # different entity: just forget
    c.emit('6a006a006a0089f9'); c.branch('e8', SET_AI_CONTROL)    # F29820(entity,0,0,0)
    absolute(c, 'ff05', stats + RESTORED)
    c.label('drop')
    absolute(c, 'c705', stats + ACTIVE); c.emit('00000000')
    c.label('native')
    c.emit('619d')
    c.branch('e9', HUD_NATIVE if hud_state else NATIVE)
    return c.finish()
