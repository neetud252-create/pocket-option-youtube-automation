import os
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, date
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
test_data = tempfile.TemporaryDirectory()
os.environ['AUTOMATION_DATA_DIR'] = test_data.name
os.environ['DISABLE_BACKGROUND_THREADS'] = '1'
from app import main, youtube, content
from app.channels import token_file


class ChannelTests(unittest.TestCase):
    def test_10pm_prepares_four_distinct_slots(self):
        now = datetime(2026, 10, 1, 22, tzinfo=main.IST)
        old = main.get_required_scheduler_slots(now)
        new = main.get_required_scheduler_slots(now, 'goplustrader')
        self.assertEqual([s.hour for s in old], [10, 18])
        self.assertEqual([s.hour for s in new], [0, 18])
        self.assertTrue(all(s.date() == date(2026, 10, 2) for s in old + new))

    def test_midnight_recovery_does_not_publish_past_slot(self):
        now = datetime(2026, 10, 2, 0, tzinfo=main.IST)
        self.assertEqual([s.hour for s in main.get_required_scheduler_slots(now, 'goplustrader')], [18])

    def test_wait_until_10pm(self):
        now = datetime(2026, 10, 1, 21, 59, tzinfo=main.IST)
        for channel in ('default', 'goplustrader'):
            self.assertEqual(main.get_required_scheduler_slots(now, channel), [])

    def test_same_time_is_independent_and_legacy_is_preserved(self):
        slot = datetime(2026, 10, 2, 18, tzinfo=main.IST)
        data = {'slots': [{'publish_at': slot.isoformat(), 'video_id': 'old'}]}
        self.assertEqual(main.missing_slots([slot], data), [])
        self.assertEqual(main.missing_slots([slot], data, 'goplustrader'), [slot])

    def test_credentials_are_separate(self):
        youtube.save_credentials(Mock(to_json=lambda: 'old'))
        youtube.save_credentials(Mock(to_json=lambda: 'new'), 'goplustrader')
        self.assertEqual(Path(token_file()).read_text(), 'old')
        self.assertEqual(Path(token_file('goplustrader')).read_text(), 'new')
        with self.assertRaises(ValueError):
            token_file('../bad')

    def test_upload_uses_requested_account(self):
        with patch.object(youtube, '_upload_video', return_value={'video_id': 'new'}) as upload:
            youtube.schedule_short('x', 'title', 'description', datetime(2026, 10, 2, tzinfo=main.IST), 'goplustrader')
            self.assertEqual(upload.call_args.kwargs['channel'], 'goplustrader')

    def test_shared_history_rejects_content_from_other_channel(self):
        history = [{'channel': 'default', 'title': 'old title', 'script': 'existing script'}]
        self.assertTrue(content.content_is_too_similar('different title', 'existing script', history)[0])

    def test_unreadable_history_stops_generation(self):
        path = Path(test_data.name) / 'broken.json'
        path.write_text('{')
        with patch.object(content, 'HISTORY_FILE', str(path)):
            with self.assertRaises(RuntimeError):
                content.load_history()

    def test_each_channel_generates_a_fresh_video_and_rerun_skips(self):
        slot = datetime(2026, 10, 2, 18, tzinfo=main.IST)
        data = {'slots': []}
        def create(publish_at, reason, channel):
            return {'publish_at': publish_at.isoformat(), 'channel': channel, 'video_id': channel}
        with patch.object(main, 'now_ist', return_value=datetime(2026, 10, 1, 22, tzinfo=main.IST)), patch.object(main, 'load_buffer', return_value=data), patch.object(main, 'save_buffer'), patch.object(main, 'automation_is_enabled', return_value=True), patch.object(main, 'create_and_schedule_short', side_effect=create) as generate:
            for channel in ('default', 'goplustrader'):
                self.assertEqual(main.fill_slots([slot], channel=channel)['created'], 1)
                self.assertEqual(main.fill_slots([slot], channel=channel)['existing'], 1)
            self.assertEqual(generate.call_count, 2)

    def test_oauth_rejects_wrong_channel_without_saving(self):
        client = main.app.test_client()
        with client.session_transaction(base_url='https://localhost') as session:
            session['oauth_state'] = 'valid'
        flow = Mock()
        main.oauth_flows['valid'] = (flow, 'goplustrader', main.time.monotonic())
        service = Mock()
        service.channels.return_value.list.return_value.execute.side_effect = [
            {'items': [{'id': 'wrong'}]}, {'items': [{'id': 'expected'}]}]
        with patch.object(main, 'build', return_value=service), patch.object(main, 'save_credentials') as save:
            response = client.get('/oauth2callback?state=valid&code=test', base_url='https://localhost')
            self.assertEqual(response.status_code, 400)
            save.assert_not_called()

    def test_oauth_accepts_only_matching_channel(self):
        client = main.app.test_client()
        with client.session_transaction(base_url='https://localhost') as session:
            session['oauth_state'] = 'valid2'
        flow = Mock()
        main.oauth_flows['valid2'] = (flow, 'goplustrader', main.time.monotonic())
        service = Mock()
        service.channels.return_value.list.return_value.execute.return_value = {'items': [{'id': 'expected'}]}
        with patch.object(main, 'build', return_value=service), patch.object(main, 'save_credentials') as save:
            response = client.get('/oauth2callback?state=valid2&code=test', base_url='https://localhost')
            self.assertEqual(response.status_code, 200)
            save.assert_called_once_with(flow.credentials, 'goplustrader')

    def test_oauth_rejects_missing_state(self):
        response = main.app.test_client().get('/oauth2callback?code=test')
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
