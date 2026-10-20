"""Verify independent production connections and scheduling for both new channels."""
import os
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DISABLE_BACKGROUND_THREADS"] = "1"
os.environ.setdefault("AUTOMATION_DATA_DIR", tempfile.mkdtemp())
from app import channels, main, youtube


NEW_CHANNELS = {
    "pockettrade": ("PocketTrade-u1l", "UCvk8MuXoNlKVzLhTOz-6J7A"),
    "zingtrader": ("zingTrader-s5t", "UCHRmFCtnW7G5IfDvKkT-dtQ"),
}


class PocketplayhubTests(unittest.TestCase):
    def test_daily_slots_and_recovery(self):
        for channel in NEW_CHANNELS:
            with self.subTest(channel=channel):
                slots = main.get_required_scheduler_slots(
                    datetime(2026, 10, 20, 22, tzinfo=main.IST), channel)
                self.assertEqual(
                    [(s.date(), s.hour, s.minute) for s in slots],
                    [(date(2026, 10, 21), 10, 0), (date(2026, 10, 21), 18, 0)])
                remaining = main.get_required_scheduler_slots(
                    datetime(2026, 10, 21, 10, tzinfo=main.IST), channel)
                self.assertEqual([s.hour for s in remaining], [18])

    def test_separate_storage_preserves_all_existing_credentials(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(channels, "DATA_DIR", directory), \
                patch.object(youtube, "DATA_DIR", directory):
            for key in channels.CHANNELS:
                youtube.save_credentials(Mock(to_json=lambda k=key: "token-" + k), key)
                channels.save_channel_metadata(key, {"title": key})
            for key in channels.CHANNELS:
                self.assertEqual(Path(channels.token_file(key)).read_text(), "token-" + key)
                self.assertEqual(channels.load_channel_metadata(key), {"title": key})
            self.assertEqual(set(channels.connected_channels()), set(channels.CHANNELS))
            self.assertEqual(len({channels.token_file(k) for k in channels.CHANNELS}), 5)

    def test_same_time_buffer_entries_are_independent(self):
        slot = datetime(2026, 10, 21, 18, tzinfo=main.IST)
        data = {"slots": [{"publish_at": slot.isoformat(), "video_id": "legacy"}]}
        self.assertEqual(main.missing_slots([slot], data, "default"), [])
        for channel in NEW_CHANNELS:
            self.assertEqual(main.missing_slots([slot], data, channel), [slot])

    def test_reuses_existing_production_client_with_offline_consent(self):
        for channel in NEW_CHANNELS:
            flow = Mock()
            flow.authorization_url.return_value = ("https://accounts.google.com/mock", channel)
            with patch.dict(os.environ, GOPLUS_YOUTUBE_CLIENT_ID="production-client",
                            GOPLUS_YOUTUBE_CLIENT_SECRET="test-secret"), \
                    patch.object(main, "SCOPES", [
                        *channels.UPLOAD_SCOPES,
                        "https://www.googleapis.com/auth/youtube.force-ssl"]), \
                    patch.object(main.Flow, "from_client_config", return_value=flow) as factory:
                response = main.app.test_client().get("/authorize?channel=" + channel)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(factory.call_args.args[0]["web"]["client_id"], "production-client")
                self.assertEqual(tuple(factory.call_args.kwargs["scopes"]), channels.UPLOAD_SCOPES)
                self.assertEqual(flow.authorization_url.call_args.kwargs["access_type"], "offline")

    def test_default_handle_cannot_be_disabled_by_empty_override(self):
        for key, (handle, _) in NEW_CHANNELS.items():
            env = channels.CHANNELS[key]["handle_env"]
            with patch.dict(os.environ, {env: ""}):
                self.assertEqual(channels.configured_handle(key), handle)
            with patch.dict(os.environ, {env: "@updated-handle"}):
                self.assertEqual(channels.configured_handle(key), "updated-handle")

    def test_oauth_saves_only_matching_channel(self):
        for key, (handle, expected_id) in NEW_CHANNELS.items():
            for matches in (False, True):
                with self.subTest(channel=key, matches=matches):
                    client = main.app.test_client()
                    state = key + str(matches)
                    with client.session_transaction(base_url="https://localhost") as session:
                        session["oauth_state"] = state
                    flow = Mock()
                    main.oauth_flows[state] = (flow, key, main.time.monotonic())
                    service = Mock()
                    actual_id = expected_id if matches else "wrong-channel"
                    service.channels.return_value.list.return_value.execute.side_effect = [
                        {"items": [{"id": actual_id, "snippet": {"title": key}}]},
                        {"items": [{"id": expected_id}]},
                    ]
                    with patch.object(main, "build", return_value=service), \
                            patch.object(main, "save_credentials") as save, \
                            patch.object(main, "save_channel_metadata") as metadata:
                        response = client.get(
                            "/oauth2callback?state=" + state + "&code=test",
                            base_url="https://localhost")
                        service.channels.return_value.list.assert_any_call(
                            part="id", forHandle=handle)
                        if matches:
                            self.assertEqual(response.status_code, 200)
                            save.assert_called_once_with(flow.credentials, key)
                            self.assertEqual(metadata.call_args.args[1]["channel_id"], expected_id)
                        else:
                            self.assertEqual(response.status_code, 400)
                            save.assert_not_called()
                            metadata.assert_not_called()

    def test_schedule_routes_to_each_new_channel(self):
        for key in NEW_CHANNELS:
            with patch.object(youtube, "_upload_video",
                              return_value={"video_id": "new-short"}) as upload:
                youtube.schedule_short("video.mp4", "Title", "Description",
                                       datetime(2026, 10, 21, 18, tzinfo=main.IST), key)
                self.assertEqual(upload.call_args.kwargs["channel"], key)

    def test_dashboard_exposes_both_new_connect_actions(self):
        with patch.object(main, "channel_connected", return_value=False), \
                patch.object(main, "load_channel_metadata", return_value={}):
            response = main.app.test_client().get("/channels")
        self.assertEqual(response.status_code, 200)
        for key in NEW_CHANNELS:
            self.assertIn(("/authorize?channel=" + key).encode(), response.data)


if __name__ == "__main__":
    unittest.main()
