"""Client stage 2 of the cutscene control (Claude 13.11.2026), on top of Codex' stage 1
(cutscene_control_policy.py, test_native_sequence_lifecycle.py, native-sequence-findings.md).

Goal: while a story AnimationSequence plays, the local human car that the scene does NOT drive is driven by the
native AI instead of rolling uncontrolled; afterwards AI off and the player's own controller back.

Static facts (client DF9F7069, Ghidra):
  * ClientAnimationSequence vtable 2488A50: Start slot +4C = 99B690 (state +14: 1 waiting, 2 running),
    Stop slot +50 = 99B770 (99A810 restores actor controllers, event 7C89BB7D, state 0). Manager [2883220]
    (vtable 24888DC): active sequences vector +0C..+10.
  * Data [seq+10] = AnimationSequenceData: +10 Controller_Private, +14 TrackIds (count at ptr-4),
    +18 TeleportActorToStartPositions[], +1C ReplaceActorsControllerOnSequenceEnd[], +20 DisableCollisions[].
  * Start (99A930) per track i: actor = 9995A0(seq, i) (thiscall, RET 4); holder = [actor+D4];
    saved[i] = [holder+1C4] into [seq+18][i]; controller := Controller_Private.
    Stop (99A810) gives saved[i] back via 5872B0(holder, saved) ONLY if ReplaceActorsControllerOnSequenceEnd[i]
    and [holder+1C4] is still Controller_Private. Without the flag the actor keeps the scene controller.
  * Local car (as the shipped pause_ai_adapter): E = [[2888F78]+BC]+318 (VT 254D220), V = [E+E4] (VT 2400150),
    V+A7C externally controlled, V+A7D animation controlled. AI switch F29820(E, enable, 0, 0) RET C
    (native AIControlSetter path, network request + local AIPlayer). AI active: [[E+7C]+8] VT 258F018, byte +20.

Hooks (RAM test, see bridge... cutscene_ai_live.py):
  P  per frame: the CALL E1D700 at E6072E (client update E606D0, ECX = level, no stack args). Builds the list of
     running sequences, resolves the actors of every newly running sequence once (is E or V an actor?), and
     reconciles AI: scene running + local car not an actor + not A7C/A7D + no AI active -> F29820(E,1,0,0);
     no scene for QUIET_LIMIT frames -> F29820(E,0,0,0), only for the AI this adapter switched on. If someone
     else switched it off meanwhile, ownership is dropped (no fighting with pause AI or the 1.51 orphan fix).
  W  vtable slot 2488AA0 (Stop): per track whose actor is E or V, the authored flag is 0, the holder still has the
     scene controller and a saved controller exists -> after the untouched native stop, if still unchanged,
     5872B0(holder, saved) exactly as native 99A810 does with the flag. Other actors untouched.
Every decision is written to a 128-entry ring (one run is enough to see what each scene did).
Registers and flags are preserved; native calls happen only at call boundaries (XMM volatile).
"""
import struct
from checkpoint_humans_adapter import Code

FRAME_SITE, FRAME_TARGET = 0xE6072E, 0xE1D700
FRAME_SITE_BYTES = bytes.fromhex('e8cdcffbff')
STOP_SLOT, STOP_NATIVE = 0x2488AA0, 0x99B770
SEQ_VT, MANAGER_VT, MANAGER = 0x2488A50, 0x24888DC, 0x2883220
ACTOR_OF, SET_CONTROLLER, SET_AI = 0x9995A0, 0x5872B0, 0xF29820
# Optional ghost (Claude 14.11.2026): native vehicle "reset ghost" = own Havok layer. Vehicle VT 2400150:
# +E8 691C70 setTimedGhost(bool) -> [V+AE2]=1, [V+B00]=3.0 s ([23FFDFC]); +F0 691CC0 setGhost(bool) -> [V+AE3].
# Per-frame vehicle update 6917A0 picks layer 8/0x17 while AE3||AE2 (else 2/0x16) and counts B00 down itself.
SET_GHOST, SET_TIMED_GHOST, GHOST_FLAG = 0x691CC0, 0x691C70, 0xAE3
ONLINE, PLAYERS = 0x2888F7C, 0x2888F78
ENTITY_VT, VEHICLE_VT, AIPLAYER_VT = 0x254D220, 0x2400150, 0x258F018
MAX_TRACKS, MAX_SEQS = 8, 8

# RW data block
FRAMES, ENGAGED, QUIET, RUNNING = 0x00, 0x04, 0x08, 0x0C
AI_ON, AI_OFF, SKIP_OWNED, SKIP_AI, CLEARED, STOPS, RESTORED, RING_SEQ = 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C
CONFIG, QUIET_LIMIT, LOCAL_ACTOR, STARTS_SEEN = 0x30, 0x34, 0x38, 0x3C
TMP = 0x40                     # 6 dwords
SEEN, SEENFLAG, CUR, CURFLAG = 0x60, 0x80, 0xA0, 0xC0
SEEN_N, CUR_N, PREV, RES, RCOUNT, SCENE_LATCH, GHOST_VEH = 0xE0, 0xE4, 0xE8, 0xEC, 0xF0, 0xF4, 0xF8
RING, ENTRIES, ENTRY = 0x100, 128, 32
DATA_SIZE = RING + ENTRIES * ENTRY
CFG_AI, CFG_RESTORE, CFG_GHOST = 1, 2, 4
CFG_DRAIN = 0x80000000  # leased helpers request native AI release before unhooking
TYPES = {1: 'sequence-running', 2: 'ai-on', 3: 'skip-owned', 4: 'skip-ai-active', 5: 'ai-cleared-by-other',
         6: 'ai-off', 7: 'stop-track', 8: 'controller-restored', 9: 'ghost-on', 10: 'ghost-off-timed'}
EAX, ECX, EDX, EBX, ESP, EBP, ESI, EDI = range(8)


def data_init(config=CFG_AI | CFG_RESTORE, quiet_limit=15):
    raw = bytearray(DATA_SIZE)
    struct.pack_into('<II', raw, CONFIG, config, quiet_limit)
    return bytes(raw)


class Asm(Code):
    """Small x86 encoder on top of Code (absolute data addresses, disp32 memory forms)."""
    def __init__(self, base, data):
        super().__init__(base); self.d = data

    def imm(self, v): self.data += struct.pack('<I', v & 0xFFFFFFFF)

    def mem(self, op, reg, base, disp):       # op r, [base+disp32]
        self.emit(op); self.data.append(0x80 | reg << 3 | base)
        if base == ESP: self.data.append(0x24)
        self.data += struct.pack('<i', disp)

    def ld(self, r, base, disp): self.mem('8b', r, base, disp)
    def st(self, base, disp, r): self.mem('89', r, base, disp)
    def lda(self, r, off): self.emit('8b'); self.data.append(r << 3 | 5); self.imm(self.d + off)
    def sta(self, off, r): self.emit('89'); self.data.append(r << 3 | 5); self.imm(self.d + off)
    def ldg(self, r, addr): self.emit('8b'); self.data.append(r << 3 | 5); self.imm(addr)   # global
    def seti(self, off, v): self.emit('c705'); self.imm(self.d + off); self.imm(v)
    def inc(self, off): self.emit('ff05'); self.imm(self.d + off)
    def cmpi(self, off, v): self.emit('813d'); self.imm(self.d + off); self.imm(v)
    def cmpm(self, base, disp, v): self.mem('81', 7, base, disp); self.imm(v)
    def cmpb(self, base, disp, v): self.mem('80', 7, base, disp); self.data.append(v)
    def cmpr(self, a, b): self.emit('39'); self.data.append(0xC0 | b << 3 | a)
    def mov(self, dst, src): self.emit('89'); self.data.append(0xC0 | src << 3 | dst)
    def test(self, r): self.emit('85'); self.data.append(0xC0 | r << 3 | r)
    def xor(self, r): self.emit('31'); self.data.append(0xC0 | r << 3 | r)
    def movi(self, r, v): self.data.append(0xB8 + r); self.imm(v)
    def idx(self, op, r, off):                # op r, [d+off + ebx*4]
        self.emit(op); self.data += bytes([r << 3 | 4, 0x9D]); self.imm(self.d + off)
    def idxc(self, op, r, off):               # op r, [d+off + ecx*4]
        self.emit(op); self.data += bytes([r << 3 | 4, 0x8D]); self.imm(self.d + off)


def lan_and_local(c, fail):
    """LAN connected client; edi = E (254D220), esi = V (2400150); else jump fail."""
    c.ldg(EAX, ONLINE); c.test(EAX); c.branch('0f84', fail)
    c.emit('80780800'); c.branch('0f85', fail)
    c.emit('83b8a400000003'); c.branch('0f85', fail)
    c.ldg(EAX, PLAYERS); c.test(EAX); c.branch('0f84', fail)
    c.ld(EAX, EAX, 0xBC); c.test(EAX); c.branch('0f84', fail)
    c.ld(EDI, EAX, 0x318); c.test(EDI); c.branch('0f84', fail)
    c.cmpm(EDI, 0, ENTITY_VT); c.branch('0f85', fail)
    c.ld(ESI, EDI, 0xE4); c.test(ESI); c.branch('0f84', fail)
    c.cmpm(ESI, 0, VEHICLE_VT); c.branch('0f85', fail)


def subroutines(c):
    # log: eax = type; TMP[0..5] -> ring entry {seq, type, tmp0..5}. Preserves everything but eax.
    c.label('log')
    c.emit('57565152')                                   # push edi, esi, ecx, edx
    c.mov(EDX, EAX)
    c.movi(EAX, 1); c.emit('f00fc105'); c.imm(c.d + RING_SEQ)
    c.mov(ECX, EAX); c.emit('83e17fc1e105')              # and ecx,7F; shl ecx,5
    c.emit('8db9'); c.imm(c.d + RING)                    # lea edi,[ecx+RING]
    c.emit('8907895704')                                 # [edi]=seq, [edi+4]=type
    c.emit('83c708'); c.movi(ESI, c.d + TMP); c.movi(ECX, 6); c.emit('f3a5')
    c.emit('5a595e5f'); c.emit('c3')
    # ai_active: edi = E -> eax = AI byte (0 = off or unknown layout)
    c.label('ai_active')
    c.ld(EAX, EDI, 0x7C); c.test(EAX); c.branch('0f84', 'ai_no')
    c.ld(EAX, EAX, 0x8); c.test(EAX); c.branch('0f84', 'ai_no')
    c.cmpm(EAX, 0, AIPLAYER_VT); c.branch('0f85', 'ai_no')
    c.emit('0fb64020c3')                                 # movzx eax, byte [eax+20]; ret
    c.label('ai_no'); c.xor(EAX); c.emit('c3')
    # resolve_local: ebp = seq, edi = E, esi = V -> eax = 1 (E is actor) | 2 (V is actor). Keeps ebx/esi/edi/ebp.
    c.label('resolve_local')
    c.emit('53'); c.xor(EBX); c.seti(RES, 0)
    c.ld(EAX, EBP, 0x10); c.test(EAX); c.branch('0f84', 'r_done')
    c.ld(EAX, EAX, 0x14); c.test(EAX); c.branch('0f84', 'r_done')
    c.emit('8b40fc'); c.emit('83f808'); c.emit('7605'); c.movi(EAX, MAX_TRACKS)
    c.sta(RCOUNT, EAX)
    c.label('r_loop')
    c.emit('3b1d'); c.imm(c.d + RCOUNT); c.branch('0f83', 'r_done')
    c.emit('53'); c.mov(ECX, EBP); c.branch('e8', ACTOR_OF)
    c.test(EAX); c.branch('0f84', 'r_next')
    c.cmpr(EAX, EDI); c.branch('0f85', 'r_v'); c.emit('830d'); c.imm(c.d + RES); c.emit('01'); c.branch('e9', 'r_next')
    c.label('r_v'); c.cmpr(EAX, ESI); c.branch('0f85', 'r_next'); c.emit('830d'); c.imm(c.d + RES); c.emit('02')
    c.label('r_next'); c.emit('43'); c.branch('e9', 'r_loop')
    c.label('r_done'); c.lda(EAX, RES); c.emit('5b'); c.emit('c3')


def clear_ant_scope(c,ant_count,context=False):
    for offset in ((0,0x0C,0x10,0x14,0x1C,0x120,0x124,0x128) if context else (0,0x14,0x1C,0x120,0x124,0x128)):
        c.emit('c705');c.imm(ant_count+offset);c.imm(0)
    # Clear cached pointer values without dereferencing any camera object.
    c.emit('515733c0bf');c.imm(ant_count+0x20)
    c.emit('b940000000f3ab5f59')


def frame_code(c, ant_count=None, ghost=False):
    c.label('frame')
    c.emit('9c60fc'); c.inc(FRAMES)
    lan_and_local(c, 'noent')
    if ant_count is not None:
        # Context is original client-update ECX (saved PUSHAD slot), then local entity.
        # Never carry camera counts into a different level or replacement vehicle.
        c.ld(EAX, ESP, 0x18)
        c.emit('3b05'); c.imm(ant_count+0x0C); c.branch('0f85', 'ant_context_reset')
        c.mov(EAX, EDI); c.emit('3b05'); c.imm(ant_count+0x10)
        c.branch('0f84', 'ant_context_ok')
        c.label('ant_context_reset')
        c.ldg(EAX,ant_count+0x0C);c.test(EAX);c.branch('0f84','ant_context_init')
        clear_ant_scope(c,ant_count)
        c.label('ant_context_init')
        c.ld(EAX, ESP, 0x18); c.emit('a3'); c.imm(ant_count+0x0C)
        c.emit('893d'); c.imm(ant_count+0x10)
        c.label('ant_context_ok')
        # Bounded fallback if a destroyed camera never emits Stop. Native
        # GetTickCount elapsed time, with unsigned subtraction across wraparound.
        # Never end a long scene early just because the user's FPS are high.
        from ant_scene_scope import GETTICK_IAT,LOST_STOP_MS,LAST_TICK,AGE_MS,CLOCK_SET
        c.ldg(EAX, ant_count); c.test(EAX); c.branch('0f84', 'ant_age_done')
        c.emit('ff05'); c.imm(ant_count+0x14)
        c.emit('ff15');c.imm(GETTICK_IAT)
        c.ldg(EDX,ant_count+CLOCK_SET);c.test(EDX);c.branch('0f85','ant_clock_ready')
        c.emit('a3');c.imm(ant_count+LAST_TICK)
        c.emit('c705');c.imm(ant_count+CLOCK_SET);c.imm(1)
        c.label('ant_clock_ready')
        c.emit('2b05');c.imm(ant_count+LAST_TICK)
        c.emit('a3');c.imm(ant_count+AGE_MS)
        c.emit('3d');c.imm(LOST_STOP_MS)
        c.branch('0f82','ant_age_done')
        c.emit('ff05');c.imm(ant_count+0x18)
        clear_ant_scope(c,ant_count)
        c.label('ant_age_done')
        # No active camera: the next one gets a fresh time origin, even on
        # same-level Retry where the engine may reuse its camera pointers.
        c.ldg(EAX,ant_count);c.test(EAX);c.branch('0f85','ant_clock_done')
        for off in (LAST_TICK,AGE_MS,CLOCK_SET):
            c.emit('c705');c.imm(ant_count+off);c.imm(0)
        c.label('ant_clock_done')
    c.lda(EAX, ENGAGED); c.test(EAX); c.branch('0f84', 'scan')
    c.cmpr(EAX, EDI); c.branch('0f84', 'scan')
    # A new pawn is a new local scene context. Do not retain the old pawn's
    # "already switched" latch or actor membership across a respawn/Retry.
    # Old pawn pointers are deliberately not dereferenced during cleanup.
    for off in (ENGAGED,SCENE_LATCH,SEEN_N,PREV):c.seti(off,0)
    c.label('scan')
    if ghost:
        # Replaced vehicle: forget ghost ownership, never touch the new one's flag on its behalf.
        c.lda(EAX, GHOST_VEH); c.test(EAX); c.branch('0f84', 'g_keep')
        c.cmpr(EAX, ESI); c.branch('0f84', 'g_keep'); c.seti(GHOST_VEH, 0)
        c.label('g_keep')
    c.seti(CUR_N, 0)
    c.emit('f705'); c.imm(c.d + CONFIG); c.imm(CFG_DRAIN)
    c.branch('0f84', 'scan_normal')
    c.xor(EBX); c.xor(EDX); c.branch('e9', 'or_done')
    c.label('scan_normal')
    c.ldg(EAX, MANAGER); c.test(EAX); c.branch('0f84', 'scanned')
    c.cmpm(EAX, 0, MANAGER_VT); c.branch('0f85', 'scanned')
    c.ld(ECX, EAX, 0x0C); c.ld(EDX, EAX, 0x10)
    c.mov(EAX, EDX); c.emit('29c8'); c.emit('3d00010000'); c.branch('0f87', 'scanned')   # bounded vector
    c.label('m_loop')
    c.cmpr(ECX, EDX); c.branch('0f83', 'scanned')
    c.emit('8b0183c104')                                  # mov eax,[ecx]; add ecx,4
    c.test(EAX); c.branch('0f84', 'm_loop')
    c.cmpm(EAX, 0, SEQ_VT); c.branch('0f85', 'm_loop')
    c.cmpm(EAX, 0x14, 2); c.branch('0f85', 'm_loop')
    c.lda(EBX, CUR_N); c.emit('83fb08'); c.branch('0f83', 'm_loop')
    c.idx('89', EAX, CUR); c.emit('c7049d'); c.imm(c.d + CURFLAG); c.imm(0)
    c.emit('43'); c.sta(CUR_N, EBX); c.branch('e9', 'm_loop')
    c.label('scanned')
    c.xor(EBX)
    c.label('c_loop')
    c.emit('3b1d'); c.imm(c.d + CUR_N); c.branch('0f83', 'c_done')
    c.idx('8b', EAX, CUR)
    c.xor(ECX)
    c.label('s_loop')
    c.emit('3b0d'); c.imm(c.d + SEEN_N); c.branch('0f83', 'new_seq')
    c.idxc('3b', EAX, SEEN); c.branch('0f84', 'found')
    c.emit('41'); c.branch('e9', 's_loop')
    c.label('found')
    c.idxc('8b', EDX, SEENFLAG); c.idx('89', EDX, CURFLAG); c.branch('e9', 'next_cur')
    c.label('new_seq')
    c.mov(EBP, EAX); c.inc(STARTS_SEEN)
    c.branch('e8', 'resolve_local')
    c.idx('89', EAX, CURFLAG)
    c.sta(TMP + 8, EAX); c.sta(TMP, EBP); c.ld(ECX, EBP, 0x10); c.sta(TMP + 4, ECX); c.sta(TMP + 12, EDI)
    c.emit('0fb68e'); c.imm(0xA7C); c.emit('0fb696'); c.imm(0xA7D)        # movzx ecx/edx, byte [esi+A7C/A7D]
    c.emit('c1e20809d1'); c.sta(TMP + 16, ECX)                            # ecx |= edx << 8
    c.lda(ECX, RCOUNT); c.sta(TMP + 20, ECX)
    c.movi(EAX, 1); c.branch('e8', 'log')
    c.label('next_cur'); c.emit('43'); c.branch('e9', 'c_loop')
    c.label('c_done')
    c.emit('5657'); c.movi(ESI, c.d + CUR); c.movi(EDI, c.d + SEEN); c.movi(ECX, 16); c.emit('f3a5'); c.emit('5f5e')
    c.lda(EBX, CUR_N); c.sta(SEEN_N, EBX)
    c.xor(EDX); c.xor(ECX)
    c.label('or_loop')
    c.cmpr(ECX, EBX); c.branch('0f83', 'or_done')
    c.idxc('0b', EDX, CURFLAG); c.emit('41'); c.branch('e9', 'or_loop')
    c.label('or_done')
    c.sta(LOCAL_ACTOR, EDX)
    # Optional experimental ANT input. Default adapter remains byte-equivalent.
    # The camera wrapper counts native active transitions, not arbitrary camera events.
    if ant_count is not None:
        # Drain must suppress ALL scene sources, including still-active cameras.
        # Otherwise cleanup can wait forever for an ANT stop that never arrives.
        c.emit('f705'); c.imm(c.d + CONFIG); c.imm(CFG_DRAIN)
        c.branch('0f85', 'ant_done')
        c.ldg(EAX, ant_count); c.test(EAX); c.branch('0f84', 'ant_done')
        c.emit('83f840'); c.branch('0f87', 'ant_done')
        c.emit('01c3')  # add ebx,eax (running count); preserve local actor flags in edx
        c.label('ant_done')
    c.lda(EAX, RUNNING); c.sta(PREV, EAX); c.sta(RUNNING, EBX)
    c.test(EBX); c.branch('0f84', 'no_scene')
    c.seti(QUIET, 0)
    if ghost:
        # Scene running: native permanent ghost on the local car, only if nobody else set it.
        c.emit('f605'); c.imm(c.d + CONFIG); c.emit('04'); c.branch('0f84', 'g_on_done')
        c.cmpi(GHOST_VEH, 0); c.branch('0f85', 'g_on_done')
        c.cmpb(ESI, GHOST_FLAG, 0); c.branch('0f85', 'g_on_done')
        c.sta(GHOST_VEH, ESI)
        c.sta(TMP, ESI); c.sta(TMP + 4, EDI); c.sta(TMP + 8, EBX)
        for k in range(3, 6): c.seti(TMP + 4 * k, 0)
        c.movi(EAX, 9); c.branch('e8', 'log')
        c.emit('526a01'); c.mov(ECX, ESI); c.branch('e8', SET_GHOST); c.emit('5a')   # keep edx (actor flags)
        c.label('g_on_done')
    c.emit('f605'); c.imm(c.d + CONFIG); c.emit('01'); c.branch('0f84', 'done')
    c.cmpi(ENGAGED, 0); c.branch('0f85', 'check_cleared')
    c.cmpi(SCENE_LATCH, 0); c.branch('0f85', 'done')      # at most one switch-on per scene: never fight
    c.test(EDX); c.branch('0f85', 'done')                 # the scene drives this car itself
    c.cmpb(ESI, 0xA7C, 0); c.branch('0f85', 'skip_owned')
    c.cmpb(ESI, 0xA7D, 0); c.branch('0f85', 'skip_owned')
    c.branch('e8', 'ai_active'); c.test(EAX); c.branch('0f85', 'skip_ai')
    c.sta(ENGAGED, EDI); c.inc(AI_ON); c.seti(SCENE_LATCH, 1)
    c.sta(TMP, EDI); c.sta(TMP + 4, ESI); c.sta(TMP + 8, EBX); c.lda(EAX, CUR); c.sta(TMP + 12, EAX)
    c.seti(TMP + 16, 0); c.seti(TMP + 20, 0)
    c.movi(EAX, 2); c.branch('e8', 'log')
    c.emit('6a006a006a01'); c.mov(ECX, EDI); c.branch('e8', SET_AI)
    c.branch('e9', 'done')
    c.label('skip_owned')
    c.cmpi(PREV, 0); c.branch('0f85', 'done')             # count once per scene start
    c.inc(SKIP_OWNED); c.sta(TMP, EDI); c.emit('0fb68e'); c.imm(0xA7C); c.sta(TMP + 4, ECX)
    c.emit('0fb68e'); c.imm(0xA7D); c.sta(TMP + 8, ECX); c.seti(TMP + 12, 0); c.seti(TMP + 16, 0); c.seti(TMP + 20, 0)
    c.movi(EAX, 3); c.branch('e8', 'log'); c.branch('e9', 'done')
    c.label('skip_ai')
    c.cmpi(PREV, 0); c.branch('0f85', 'done')
    c.inc(SKIP_AI); c.sta(TMP, EDI); c.sta(TMP + 4, EAX)
    c.seti(TMP + 8, 0); c.seti(TMP + 12, 0); c.seti(TMP + 16, 0); c.seti(TMP + 20, 0)
    c.movi(EAX, 4); c.branch('e8', 'log'); c.branch('e9', 'done')
    c.label('check_cleared')
    c.branch('e8', 'ai_active'); c.test(EAX); c.branch('0f85', 'done')
    c.inc(CLEARED); c.seti(ENGAGED, 0); c.sta(TMP, EDI)
    for k in range(1, 6): c.seti(TMP + 4 * k, 0)
    c.movi(EAX, 5); c.branch('e8', 'log'); c.branch('e9', 'done')
    c.label('no_scene')
    c.inc(QUIET); c.seti(SCENE_LATCH, 0)
    if ghost:
        # Scene over (same quiet limit as AI): own permanent ghost off, native 3 s timed ghost as the after-run.
        c.cmpi(GHOST_VEH, 0); c.branch('0f84', 'g_off_done')
        c.lda(EAX, QUIET); c.emit('3b05'); c.imm(c.d + QUIET_LIMIT); c.branch('0f82', 'g_off_done')
        c.seti(GHOST_VEH, 0)
        c.emit('0fb686'); c.imm(GHOST_FLAG)                   # movzx eax, byte [esi+AE3]
        c.sta(TMP, ESI); c.sta(TMP + 4, EAX)
        for k in range(2, 6): c.seti(TMP + 4 * k, 0)
        c.test(EAX); c.branch('0f84', 'g_no_perm')            # cleared by someone else: leave it
        c.emit('6a00'); c.mov(ECX, ESI); c.branch('e8', SET_GHOST)
        c.label('g_no_perm')
        c.emit('6a01'); c.mov(ECX, ESI); c.branch('e8', SET_TIMED_GHOST)
        c.movi(EAX, 10); c.branch('e8', 'log')
        c.label('g_off_done')
    c.cmpi(ENGAGED, 0); c.branch('0f84', 'done')
    c.lda(EAX, QUIET); c.emit('3b05'); c.imm(c.d + QUIET_LIMIT); c.branch('0f82', 'done')
    c.seti(ENGAGED, 0); c.inc(AI_OFF)
    c.branch('e8', 'ai_active')
    c.sta(TMP, EDI); c.sta(TMP + 4, EAX)
    for k in range(2, 6): c.seti(TMP + 4 * k, 0)
    c.emit('50'); c.movi(EAX, 6); c.branch('e8', 'log'); c.emit('58')
    c.test(EAX); c.branch('0f84', 'done')                 # already off: nothing to give back
    c.emit('6a006a006a00'); c.mov(ECX, EDI); c.branch('e8', SET_AI)
    c.branch('e9', 'done')
    c.label('noent')
    for off in (ENGAGED,SCENE_LATCH,SEEN_N,CUR_N,RUNNING,LOCAL_ACTOR,QUIET):c.seti(off,0)
    if ghost: c.seti(GHOST_VEH, 0)
    if ant_count is not None:clear_ant_scope(c,ant_count,context=True)
    c.label('done')
    c.emit('619d'); c.branch('e9', FRAME_TARGET)


def stop_code(c):
    # Frame: [esp]=seq, [esp+4+4i]=holder[i], [esp+24+4i]=saved[i], [esp+44]=scene controller, [esp+48]=count
    c.label('stop')
    c.emit('9c60fc'); c.emit('83ec4c'); c.emit('890c24')
    c.xor(EAX); c.emit('8d7c2404'); c.movi(ECX, 16); c.emit('f3ab')
    c.inc(STOPS)
    c.emit('f605'); c.imm(c.d + CONFIG); c.emit('02'); c.branch('0f84', 'w_call')
    lan_and_local(c, 'w_call')
    c.emit('8b2c24')                                      # ebp = seq
    c.cmpm(EBP, 0x14, 0); c.branch('0f84', 'w_call')      # native stop does nothing in state 0
    c.ld(EAX, EBP, 0x10); c.test(EAX); c.branch('0f84', 'w_call')
    c.ld(EDX, EAX, 0x10); c.emit('89542444')              # scene controller
    c.ld(ECX, EAX, 0x14); c.test(ECX); c.branch('0f84', 'w_call')
    c.emit('8b49fc83f9087605'); c.movi(ECX, MAX_TRACKS); c.emit('894c2448')
    c.xor(EBX)
    c.label('w_loop')
    c.emit('3b5c2448'); c.branch('0f83', 'w_call')
    c.emit('53'); c.mov(ECX, EBP); c.branch('e8', ACTOR_OF)
    c.test(EAX); c.branch('0f84', 'w_next')
    c.xor(EDX); c.cmpr(EAX, EDI); c.branch('0f85', 'w_v'); c.movi(EDX, 1); c.branch('e9', 'w_m')
    c.label('w_v'); c.cmpr(EAX, ESI); c.branch('0f85', 'w_m'); c.movi(EDX, 2)
    c.label('w_m')
    c.sta(TMP, EBP); c.sta(TMP + 4, EBX); c.sta(TMP + 8, EAX); c.sta(TMP + 12, EDX)
    c.ld(ECX, EBP, 0x10); c.ld(ECX, ECX, 0x1C); c.test(ECX); c.emit('7404'); c.emit('0fb60c19')
    c.sta(TMP + 16, ECX)                                  # authored ReplaceActorsControllerOnSequenceEnd[i]
    c.ld(ECX, EAX, 0xD4); c.sta(TMP + 20, ECX)            # holder
    c.emit('50'); c.movi(EAX, 7); c.branch('e8', 'log'); c.emit('58')
    c.test(EDX); c.branch('0f84', 'w_next')               # not the local car
    c.cmpi(TMP + 16, 0); c.branch('0f85', 'w_next')       # native restores itself
    c.ld(ECX, EAX, 0xD4); c.test(ECX); c.branch('0f84', 'w_next')
    c.ld(EDX, ECX, 0x1C4); c.emit('3b542444'); c.branch('0f85', 'w_next')
    c.ld(EDX, EBP, 0x18); c.test(EDX); c.branch('0f84', 'w_next')
    c.emit('8b149a'); c.test(EDX); c.branch('0f84', 'w_next')             # saved controller
    c.emit('894c9c04'); c.emit('89549c24')
    c.label('w_next')
    c.emit('43'); c.branch('e9', 'w_loop')
    c.label('w_call')
    c.emit('8b0c24'); c.branch('e8', STOP_NATIVE)         # untouched native stop
    c.xor(EBX)
    c.label('p_loop')
    c.emit('8b4c9c04'); c.test(ECX); c.branch('0f84', 'p_next')
    c.ld(EDX, ECX, 0x1C4); c.emit('3b542444'); c.branch('0f85', 'p_next')  # still the scene controller
    c.emit('8b449c24')
    c.emit('8b1424'); c.sta(TMP, EDX); c.sta(TMP + 4, EBX); c.sta(TMP + 8, ECX); c.sta(TMP + 12, EAX)
    c.emit('8b542444'); c.sta(TMP + 16, EDX); c.seti(TMP + 20, 0)
    c.emit('5051'); c.movi(EAX, 8); c.branch('e8', 'log'); c.emit('5958')
    c.emit('50'); c.branch('e8', SET_CONTROLLER)          # 5872B0(holder, saved), RET 4
    c.inc(RESTORED)
    c.label('p_next')
    c.emit('4383fb08'); c.branch('0f82', 'p_loop')
    # The engine can stop and restart the same sequence object between frames.
    # Re-resolve actor membership next frame rather than reusing that object's
    # pre-Retry classification. Existing AI ownership is reconciled normally.
    c.seti(SEEN_N,0)
    c.emit('83c44c619dc3')


def make_code(base, data, ant_count=None, ghost=False):
    """Returns (code, {'frame': entry, 'stop': entry}). ghost=False keeps the earlier bytes exactly."""
    c = Asm(base, data)
    frame_code(c, ant_count, ghost); stop_code(c); subroutines(c)
    code = c.finish()
    return code, {'frame': c.labels['frame'], 'stop': c.labels['stop']}


def decode_counters(raw):
    names = ('frames', 'engaged', 'quiet', 'running', 'ai_on', 'ai_off', 'skip_owned', 'skip_ai', 'cleared',
             'stops', 'restored', 'ring_seq', 'config', 'quiet_limit', 'local_actor', 'starts_seen')
    vals = struct.unpack_from('<16I', raw)
    out = dict(zip(names, vals)); out['engaged'] = hex(out['engaged'])
    return out


def decode_ring(raw, after=0):
    rows = []
    for i in range(ENTRIES):
        seq, typ, *p = struct.unpack_from('<8I', raw, RING + i * ENTRY)
        if typ and seq >= after:
            rows.append(dict(seq=seq, type=TYPES.get(typ, typ), values=[hex(v) for v in p]))
    return sorted(rows, key=lambda r: r['seq'])
