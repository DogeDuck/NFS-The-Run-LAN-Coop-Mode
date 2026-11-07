"""1.51 test mode: native failed-restore path, explicit Select -> shared Retry."""
import struct
from checkpoint_humans_adapter import Code
from orphan_spawn_release_adapter import GUID
SERVER_SITE=0x13FA023
SERVER_TARGET=0x2B7E000
SERVER_FAILED=0x13FA042
CLIENT_SITE=0x8ECA70
CLIENT_ORIGINAL=bytes.fromhex('83ec28568bf1')


def _guid(c, register, fail):
 for i,word in enumerate(struct.unpack('<4I',GUID.bytes_le)):
  c.emit('81'+register+bytes([0xf0+i*4]).hex());c.data+=struct.pack('<I',word);c.branch('0f85',fail)


def server_code(base,stats):
 c=Code(base)
 def absolute(op,value):c.emit(op);c.data+=struct.pack('<I',value)
 c.emit('9c60')
 # This is specifically the three-argument Restore call in13F9F70.
 c.emit('817c242428a03f01');c.branch('0f85','fallback')
 # All bookmark reasons, including ManualRewind0, are rejected in this test.
 # Select uses a distinct RestartChallengeMessage via the native UI action.
 c.emit('8b44242c')
 c.emit('83f804');c.branch('0f87','fallback')
 absolute('a1',0x28E5C80);c.emit('85c0');c.branch('0f84','fallback')
 c.emit('8138506d5b02');c.branch('0f85','fallback')
 c.emit('8b401085c0');c.branch('0f84','fallback');_guid(c,'78','fallback')
 # Fail closed unless exactly two human racers are in active Racing state.
 # Loading/uninitialized cars must never trigger the automatic both-dead retry.
 absolute('a1',0x28E5C90);c.emit('85c0');c.branch('0f84','not_both_dead')
 c.emit('8b906c0500008b807005000029d083f808');c.branch('0f85','not_both_dead')
 for index in range(2):
  c.emit('8b0a' if index==0 else '8b4a04')
  c.emit('85c9');c.branch('0f84','not_both_dead')
  c.emit('83791400');c.branch('0f85','not_both_dead')
  c.emit('83791806');c.branch('0f85','not_both_dead')
 absolute('a1',0x28A3220);c.emit('85c0');c.branch('0f84','not_both_dead')
 c.emit('8b80a400000085c0');c.branch('0f84','not_both_dead')
 for index in range(2):
  c.emit('8b08' if index==0 else '8b4804')
  c.emit('85c9');c.branch('0f84','not_both_dead')
  c.emit('80b96002000000');c.branch('0f85','not_both_dead')
  c.emit('83b9e4020000'+bytes([index]).hex());c.branch('0f85','not_both_dead')
  c.emit('8b890803000085c9');c.branch('0f84','not_both_dead')
  c.emit('8139c8835902');c.branch('0f85','not_both_dead')
  c.emit('8b910002000085d2');c.branch('0f85','wrapper_'+str(index))
  c.emit('8b910402000085d2');c.branch('0f84','not_both_dead')
  c.label('wrapper_'+str(index))
  c.emit('8b8a9400000085c9');c.branch('0f84','not_both_dead')
  c.emit('813950014002');c.branch('0f85','not_both_dead')
  c.emit('83b9c001000000');c.branch('0f84','not_both_dead')
  c.emit('83b9c801000004');c.branch('0f85','not_both_dead')
  c.emit('83b97818000000');c.branch('0f85','not_both_dead')
 # Native full retry only for two initialized, actually dead cars. Debounce
 # repeated requests while the server begins replacing the current round.
 absolute('ff15',0x2A8B8E4)
 c.emit('89c2');absolute('2b05',stats+12)
 c.emit('3d88130000');c.branch('0f82','not_both_dead')
 absolute('8915',stats+12);absolute('ff05',stats+8)
 c.branch('e9','fallback')
 c.label('not_both_dead')
 absolute('ff05',stats)
 # Do NOT broadcast RestoreAttemptFailed: that fails/blocks the other player.
 # Complete the pending reset UI/network handshake without restoring the world.
 # This follows the native RestoreDone message's local+network send sequence.
 c.emit('8b742418813e34da5b02');c.branch('0f85','fallback')
 c.emit('89e581ec6002000083e4f00fae442440')
 c.emit('c786e800000000000000c786ec00000000000000')
 c.emit('89e1');c.branch('e8',0x231C450)
 c.emit('8bc450');absolute('8b0d',0x28A31FC);c.branch('e8',0x4F1D80)
 c.emit('8bc45089f1');c.branch('e8',0x13F5360)
 c.emit('89e1');c.branch('e8',0x18507E0)
 c.emit('0fae4c244089ec619dc20c00')
 c.label('fallback');c.emit('619d');c.branch('e9',SERVER_TARGET)
 return c.finish()


def client_code(base,stats):
 c=Code(base)
 def absolute(op,value):c.emit(op);c.data+=struct.pack('<I',value)
 c.emit('9c60')
 absolute('a1',0x2888F7C);c.emit('85c0');c.branch('0f84','fallback')
 c.emit('80780800');c.branch('0f85','fallback')
 c.emit('83b8a400000003');c.branch('0f85','fallback')
 absolute('a1',0x28824E8);c.emit('85c0');c.branch('0f84','fallback')
 c.emit('8138a8a84702');c.branch('0f85','fallback')
 c.emit('89c78b401085c0');c.branch('0f84','fallback');_guid(c,'78','fallback')
 c.emit('89e581ec2002000083e4f00fae0424')
 absolute('ff15',0x2A8B8E4) # verified32-bit GetTickCount IAT
 c.emit('89c2');absolute('2b05',stats+4)
 c.emit('3de8030000');c.branch('0f82','done')
 absolute('8915',stats+4)
 absolute('ff05',stats)
 c.emit('6a0189f9');c.branch('e8',0x864350) # Native story-controller Retry(1), RET4
 c.label('done');c.emit('0fae0c2489ec619dc20400')
 c.label('fallback');c.emit('619d');c.data+=CLIENT_ORIGINAL;c.branch('e9',CLIENT_SITE+6)
 return c.finish()
