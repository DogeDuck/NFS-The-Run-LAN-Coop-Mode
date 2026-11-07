"""Compose the current experimental reset policy with the checkpoint server patch."""
import struct
from patch_coop_checkpoints import build as checkpoints
from patch_story_spawn_1_51 import build as spawn
from patch_headless_reset import file_offset, digest
from pe_adapter import append_adapter
from probe_lifecycle import call_bytes
from manual_retry_mode_adapter import SERVER_SITE, SERVER_TARGET, server_code

def build_client(base):
    return spawn(base, manual_restart=True)

def build_server(base,reserve_authored_slots=False,battle_team_finish=False,gas_ack_timeout=False):
    staged, _, report = checkpoints(base)
    off = file_offset(staged, SERVER_SITE)
    if staged[off:off+5] != call_bytes(SERVER_SITE, SERVER_TARGET):
        raise ValueError('Unexpected reset policy baseline')
    patched, layout, code, _ = append_adapter(staged, server_code, b'.rstmode', b'.rststat')
    patched[off:off+5] = call_bytes(SERVER_SITE, layout['adapter'])
    pe = struct.unpack_from('<I', patched, 0x3c)[0]
    count = struct.unpack_from('<H', patched, pe+6)[0]
    table = pe+24+struct.unpack_from('<H', patched, pe+20)[0]
    struct.pack_into('<I', patched, table+40*(count-1)+8, 16)
    report.update(patched_sha256=digest(patched), reset_layout=layout,
                  validation=[report['validation'], 'Experimental manual reset policy; timeout, both-dead retry and story progression need live testing'])
    from patch_story_ai_gate import build as add_ai_gate
    final, ai_code, ai_report = add_ai_gate(bytes(patched))
    report.update(patched_sha256=digest(final), ai_gate=ai_report)
    from patch_story_start_spawn import build as add_story_start
    final,spawn_code,spawn_report=add_story_start(final,reserve_authored_slots)
    report.update(patched_sha256=digest(final),story_start=spawn_report)
    if battle_team_finish:
        # Opt-in DRAFT (ELIMINATOR-FINISH-2026-11-04.md): every human finishes BattleRace together.
        from patch_battle_team_finish import build as add_battle_finish
        final,battle_code,battle_report=add_battle_finish(final)
        spawn_code+=battle_code
        report.update(patched_sha256=digest(final),battle_team_finish=battle_report)
    if gas_ack_timeout:
        # Opt-in DRAFT (ERGEBNISSE-FUER-CHATGPT-2026-11-05.md): continue the bundle queue when client acks never come.
        from patch_gas_ack_timeout import build as add_gas_ack
        final,gas_code,gas_report=add_gas_ack(final)
        spawn_code+=gas_code
        report.update(patched_sha256=digest(final),gas_ack_timeout=gas_report)
    return final, code+ai_code+spawn_code, report
