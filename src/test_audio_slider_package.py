"""Only the slider mix can be installed; legacy boost bytes are migration inputs."""
import base64,gzip,json,unittest
from pathlib import Path
from build_integrated_selected_candidate import assert_slider_audio

class AudioSliderTests(unittest.TestCase):
    def test_current_payload_has_zero_global_boost_and_no_legacy_target_option(self):
        source=Path(__file__).resolve().parent/'third_party/coop-addons/music25/NFS-Audio-Patch.ps1'
        payload=assert_slider_audio(source.read_text(encoding='utf-8-sig'))
        self.assertEqual(payload['music_db'],0)
    def test_builder_refuses_fixed_boost_even_if_marked_target(self):
        payload=dict(music_db=25,states=['Original','Target'])
        encoded=base64.b64encode(gzip.compress(json.dumps(payload).encode())).decode()
        script="[ValidateSet('Apply','Restore')]\n$encoded='"+encoded+"'"
        with self.assertRaises(ValueError):assert_slider_audio(script)

if __name__=='__main__':unittest.main()
