import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, date
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DISABLE_BACKGROUND_THREADS'] = '1'
os.environ.setdefault('AUTOMATION_DATA_DIR', tempfile.mkdtemp())
from app import main, youtube, video
from app import content
from app.channels import CHANNELS, channel_connected
from app.upload_ledger import UploadLedger


class ThirdChannelTests(unittest.TestCase):
    def test_old_exact_script_is_rejected_beyond_similarity_window(self):
        history = [{'title': 'original', 'script': 'first script'}]
        history += [{'title': f'title {i}', 'script': f'script {i}'} for i in range(200)]
        self.assertTrue(content.content_is_too_similar('fresh title', 'first script', history)[0])

    def test_clip_sequence_cannot_repeat_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            history = str(Path(directory, 'sequences.json'))
            clips = [str(Path(directory, f'{i}.mp4')) for i in range(5)]
            with patch.object(video, 'CLIP_HISTORY_FILE', history), patch.object(video, 'DATA_DIR', directory), patch.object(video, 'available_random_clips', return_value=clips), patch.object(video.random, 'sample', side_effect=[clips[:4], clips[:4], clips[1:]]):
                first = video.select_random_clips()
                second = video.select_random_clips()
                self.assertNotEqual(first, second)

    def test_manual_test_routes_to_channel3_with_same_description(self):
        with patch.object(main, 'ensure_preflight_ready'), patch.object(main, 'generate_content', return_value=('fresh title', 'fresh script')), patch.object(main, 'generate_voice'), patch.object(main, 'generate_video', return_value='video.mp4'), patch.object(main, 'upload_short', return_value='test-video') as upload, patch.object(main.UploadLedger, 'lookup', return_value=None), patch.object(main, 'safe_remove'):
            result = main.create_and_upload_short('channel3', 'one-test')
            self.assertEqual(upload.call_args.kwargs['channel'], 'channel3')
            self.assertEqual(upload.call_args.kwargs['description'], main.YOUTUBE_DESCRIPTION)
            self.assertEqual(upload.call_args.kwargs['test_id'], 'one-test')
            self.assertEqual(result['privacy_status'], 'unlisted')

    def test_manual_test_recovers_existing_receipt_without_generating(self):
        with patch.object(main, 'ensure_preflight_ready'), patch.object(main.UploadLedger, 'lookup', return_value={'video_id': 'existing'}), patch.object(main, 'generate_content') as generate:
            self.assertEqual(main.create_and_upload_short('channel3', 'one-test')['video_id'], 'existing')
            generate.assert_not_called()

    def test_channel3_uses_its_own_oauth_client(self):
        flow = Mock()
        flow.authorization_url.return_value = ('https://accounts.google.com/mock', 'separate')
        with patch.dict(CHANNELS['channel3'], handle='traderFx-x9d'), patch.dict(os.environ, YOUTUBE_CHANNEL3_CLIENT_ID='new-client', YOUTUBE_CHANNEL3_CLIENT_SECRET='new-secret', YOUTUBE_CLIENT_ID='old-client', YOUTUBE_CLIENT_SECRET='old-secret'), patch.object(main.Flow, 'from_client_config', return_value=flow) as factory:
            response = main.app.test_client().get('/authorize?channel=channel3', base_url='https://localhost')
            self.assertEqual(response.status_code, 302)
            config = factory.call_args.args[0]['web']
            self.assertEqual(config['client_id'], 'new-client')
            self.assertEqual(config['client_secret'], 'new-secret')

    def test_missing_channel3_client_does_not_use_original(self):
        with patch.dict(CHANNELS['channel3'], handle='traderFx-x9d'), patch.dict(os.environ, YOUTUBE_CHANNEL3_CLIENT_ID='', YOUTUBE_CHANNEL3_CLIENT_SECRET='', YOUTUBE_CLIENT_ID='old-client', YOUTUBE_CLIENT_SECRET='old-secret'), patch.object(main.Flow, 'from_client_config') as factory:
            response = main.app.test_client().get('/authorize?channel=channel3')
            self.assertEqual(response.status_code, 500)
            factory.assert_not_called()

    def test_schedule_and_midnight_recovery(self):
        slots = main.get_required_scheduler_slots(datetime(2026, 10, 1, 22, tzinfo=main.IST), 'channel3')
        self.assertEqual([(s.date(), s.hour, s.minute) for s in slots], [(date(2026, 10, 2), 1, 0), (date(2026, 10, 2), 6, 0)])
        self.assertEqual([s.hour for s in main.get_required_scheduler_slots(datetime(2026, 10, 2, 2, tzinfo=main.IST), 'channel3')], [6])
        self.assertEqual(main.get_required_scheduler_slots(datetime(2026, 10, 2, 6, tzinfo=main.IST), 'channel3'), [])

    def test_env_connection_requires_handle_and_token(self):
        with patch.dict(CHANNELS['channel3'], handle='traderFx-x9d'), patch.dict(os.environ, YOUTUBE_CHANNEL3_TOKEN_JSON='test'):
            self.assertTrue(channel_connected('channel3'))
        with patch.dict(CHANNELS['channel3'], handle=''):
            self.assertFalse(channel_connected('channel3'))

    def test_oauth_returns_env_token_without_persisting(self):
        client = main.app.test_client()
        with client.session_transaction(base_url='https://localhost') as session:
            session['oauth_state'] = 'third'
        flow = Mock()
        flow.credentials.to_json.return_value = '{"refresh_token":"mock"}'
        main.oauth_flows['third'] = (flow, 'channel3', main.time.monotonic())
        service = Mock()
        service.channels.return_value.list.return_value.execute.return_value = {'items': [{'id': 'third-id'}]}
        with patch.dict(CHANNELS['channel3'], handle='traderFx-x9d'), patch.object(main, 'build', return_value=service), patch.object(main, 'save_credentials') as save:
            response = client.get('/oauth2callback?state=third&code=test', base_url='https://localhost')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['railway_variable'], 'YOUTUBE_CHANNEL3_TOKEN_JSON')
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            save.assert_not_called()

    def test_discovers_all_25_clips_excludes_cta(self):
        with tempfile.TemporaryDirectory() as directory:
            for index in range(25):
                Path(directory, f'{index:02d}_clip.mp4').touch()
            Path(directory, 'activation_cta.mp4').touch()
            with patch.object(video, 'ASSETS_DIR', directory):
                self.assertEqual(len(video.available_random_clips()), 25)
                self.assertEqual(len(set(video.select_random_clips())), 4)

    def test_corrupt_buffer_blocks_reupload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'buffer.json')
            path.write_text('{')
            with patch.object(main, 'BUFFER_FILE', str(path)), self.assertRaises(RuntimeError):
                main.load_buffer()

    def test_no_earnings_claim_in_overlay(self):
        overlay = video.opening_overlay(2000)
        self.assertNotIn('I MADE', overlay)
        self.assertNotIn('$2000', overlay)
        self.assertIn('TRADING INVOLVES RISK', overlay)

    def test_restart_recovers_receipt_without_new_content(self):
        slot = datetime(2026, 10, 2, 1, tzinfo=main.IST)
        receipt = {'video_id': 'existing-id', 'title': 'Original title', 'publish_at': slot.isoformat(), 'channel': 'channel3'}
        with patch.object(main, 'automation_is_enabled', return_value=True), patch.object(main, 'ensure_preflight_ready'), patch.object(main, 'now_ist', return_value=slot.replace(day=1, hour=22)), patch.object(main.UploadLedger, 'lookup', return_value=receipt), patch.object(main, 'get_thumbnail_status', return_value={}), patch.object(main, 'generate_content') as content:
            self.assertEqual(main.create_and_schedule_short(slot, channel='channel3')['video_id'], 'existing-id')
            content.assert_not_called()


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = UploadLedger(str(Path(self.directory.name, 'ledger.json')))
        self.video = Path(self.directory.name, 'test.mp4')
        self.video.write_bytes(b'unique rendered video')
        self.slot = datetime(2026, 10, 2, 1, tzinfo=main.IST)

    def test_uncertain_upload_survives_restart(self):
        self.ledger.begin('channel3', self.slot, str(self.video))
        with self.assertRaises(RuntimeError):
            UploadLedger(self.ledger.path).begin('channel3', self.slot, str(self.video))

    def test_unlisted_test_receipt_prevents_second_upload(self):
        self.ledger.begin('channel3', 'one-test', str(self.video))
        self.ledger.complete('channel3', 'one-test', 'unlisted-id')
        self.assertEqual(self.ledger.lookup('channel3', 'one-test')['privacy_status'], 'unlisted')
        self.assertEqual(self.ledger.begin('channel3', 'one-test', str(self.video))['video_id'], 'unlisted-id')

    def test_completed_upload_reused_without_insert(self):
        self.ledger.begin('channel3', self.slot, str(self.video))
        self.ledger.complete('channel3', self.slot, 'remote-id')
        self.assertEqual(self.ledger.begin('channel3', self.slot, str(self.video))['video_id'], 'remote-id')

    def test_video_id_saved_before_followup_failure_and_no_reupload(self):
        service = Mock()
        request = service.videos.return_value.insert.return_value
        request.next_chunk.return_value = (None, {'id': 'remote-id'})
        with patch.object(youtube, 'get_youtube_service', return_value=service), patch.object(youtube, 'MediaFileUpload'), patch.object(youtube, 'UploadLedger', return_value=self.ledger), patch.object(youtube, 'apply_short_thumbnail', side_effect=RuntimeError('follow-up failed')):
            with self.assertRaises(RuntimeError):
                youtube._upload_video(str(self.video), 'title', 'description', 'private', self.slot, 'channel3')
            recovered = youtube._upload_video(str(self.video), 'title', 'description', 'private', self.slot, 'channel3')
            self.assertEqual(recovered['video_id'], 'remote-id')
            self.assertEqual(request.next_chunk.call_count, 1)

    def test_exact_video_blocked_across_channels(self):
        self.ledger.begin('channel3', self.slot, str(self.video))
        with self.assertRaises(RuntimeError):
            self.ledger.begin('default', self.slot.replace(hour=10), str(self.video))

    def test_cooldown_and_off_schedule_limit(self):
        self.ledger.begin('channel3', self.slot, str(self.video))
        self.ledger.complete('channel3', self.slot, 'remote-id')
        self.video.write_bytes(b'another video')
        with self.assertRaises(RuntimeError):
            self.ledger.begin('channel3', self.slot.replace(hour=6), str(self.video))
        with self.assertRaises(ValueError):
            self.ledger.begin('channel3', self.slot.replace(hour=7), str(self.video))

    def test_corrupt_ledger_blocks_upload(self):
        Path(self.ledger.path).write_text('{')
        with self.assertRaises(RuntimeError):
            self.ledger.begin('channel3', self.slot, str(self.video))

