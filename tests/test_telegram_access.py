import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import telegram


class TelegramAccessFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.original_file = telegram.USER_ACCESS_FILE
        telegram.USER_ACCESS_FILE = os.path.join(
            self.temporary.name,
            "telegram_user_access.json",
        )

    def tearDown(self):
        telegram.USER_ACCESS_FILE = self.original_file
        self.temporary.cleanup()

    def test_admin_uploaded_gift_is_delivered_and_recorded(self):
        telegram.set_gift_document({
            "file_id": "telegram-file-id",
            "file_unique_id": "unique-file-id",
            "file_name": "Apex Trader Money Management.xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }, 999)
        telegram.update_user_record(
            101,
            state="UID_VERIFIED",
            broker_uid="UID101",
        )

        with patch.object(
            telegram,
            "send_document",
            return_value={"ok": True, "result": {"message_id": 55}},
        ) as send_document:
            self.assertTrue(telegram.deliver_gift(101))

        send_document.assert_called_once()
        user = telegram.get_user_record(101)
        self.assertEqual("GIFT_SENT", user["state"])
        self.assertEqual(55, user["gift_message_id"])

    def test_uid_cannot_be_claimed_by_two_users(self):
        telegram.update_user_record(101, broker_uid="ABC-123")
        self.assertEqual("101", telegram.uid_owner("abc-123"))
        self.assertIsNone(
            telegram.uid_owner("abc-123", excluding_user_id=101)
        )

    def test_verified_deposit_grants_access(self):
        telegram.update_user_record(
            202,
            state="GIFT_ACKNOWLEDGED",
            broker_uid="UID202",
        )
        profile = {"id": 202, "first_name": "Test"}

        with patch.object(telegram, "answer_callback"), patch.object(
            telegram,
            "send_message",
        ) as send_message, patch.object(
            telegram,
            "verify_deposit_with_provider",
            return_value={
                "status": "verified",
                "amount": 100.0,
                "reference": "deposit-1",
            },
        ):
            telegram.handle_user_callback(
                "callback-1",
                202,
                profile,
                "user:start_trading",
            )

        user = telegram.get_user_record(202)
        self.assertEqual("ACCESS_GRANTED", user["state"])
        self.assertEqual(100.0, user["deposit_amount"])
        self.assertGreaterEqual(send_message.call_count, 1)

    def test_missing_provider_routes_uid_to_manual_review(self):
        with patch.object(telegram, "UID_VERIFY_URL", ""):
            result = telegram.verify_uid_with_provider("UID303", 303)
        self.assertEqual("manual_review", result["status"])

    def test_old_gift_buttons_do_not_downgrade_access(self):
        telegram.update_user_record(
            404,
            state="ACCESS_GRANTED",
            broker_uid="UID404",
        )
        profile = {"id": 404, "first_name": "Test"}

        with patch.object(telegram, "answer_callback") as answer, patch.object(
            telegram,
            "send_message",
        ), patch.object(telegram, "send_document") as send_document:
            telegram.handle_user_callback(
                "old-claim",
                404,
                profile,
                "user:claim_gift",
            )
            telegram.handle_user_callback(
                "old-confirm",
                404,
                profile,
                "user:gift_received",
            )

        self.assertEqual("ACCESS_GRANTED", telegram.get_user_record(404)["state"])
        send_document.assert_not_called()
        self.assertEqual(2, answer.call_count)


if __name__ == "__main__":
    unittest.main()
