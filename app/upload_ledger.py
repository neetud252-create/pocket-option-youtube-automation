"""Durable scheduled-upload receipts. Uncertain uploads require reconciliation."""
import hashlib
import json
import os
import threading
import time
from zoneinfo import ZoneInfo
from app.channels import DATA_DIR, channel_profile
from app.storage_lock import storage_lock

LOCK = threading.RLock()
COOLDOWN_SECONDS = 300


class UploadLedger:
    def __init__(self, path=None):
        self.path = path or os.path.join(DATA_DIR, "upload_ledger.json")

    def load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as stream:
                records = json.load(stream)
            if not isinstance(records, dict) or any(not isinstance(r, dict) for r in records.values()):
                raise ValueError("Invalid ledger")
            return records
        except Exception as exc:
            raise RuntimeError("Upload ledger is unreadable; restore it before uploading.") from exc

    def save(self, records):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path + ".tmp", "w", encoding="utf-8") as stream:
            json.dump(records, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(self.path + ".tmp", self.path)

    @staticmethod
    def key(channel, publish_at):
        if isinstance(publish_at, str):
            return channel + "|test|" + publish_at
        return channel + "|" + publish_at.astimezone(ZoneInfo("Asia/Kolkata")).isoformat()

    def lookup(self, channel, publish_at):
        with LOCK, storage_lock(self.path):
            record = self.load().get(self.key(channel, publish_at))
            if record and not record.get("video_id"):
                raise RuntimeError("Upload outcome is uncertain. Check YouTube Studio and reconcile upload_ledger.json; automatic reupload is blocked.")
            return record

    def begin(self, channel, publish_at, video_path, title=""):
        channel_profile(channel)
        local = None if isinstance(publish_at, str) else publish_at.astimezone(ZoneInfo("Asia/Kolkata"))
        if local and ((local.hour, local.minute) not in channel_profile(channel)["times"] or local.second or local.microsecond):
            raise ValueError("Scheduled uploads must use a configured daily slot.")
        digest = hashlib.sha256()
        with open(video_path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        fingerprint = digest.hexdigest()
        clips = []
        if os.path.exists(video_path + ".clips.json"):
            with open(video_path + ".clips.json", encoding="utf-8") as stream:
                clips = json.load(stream)
        with LOCK, storage_lock(self.path):
            records = self.load()
            existing = records.get(self.key(channel, publish_at))
            if existing:
                if not existing.get("video_id"):
                    raise RuntimeError("Upload outcome is uncertain; automatic reupload is blocked.")
                return existing
            now = time.time()
            for record in records.values():
                if record.get("sha256") == fingerprint:
                    raise RuntimeError("This exact video was already submitted on a channel.")
                if record.get("channel") == channel and now - record.get("completed_at", record["started_at"]) < COOLDOWN_SECONDS:
                    raise RuntimeError("Channel upload cooldown is active; retry after five minutes.")
            records[self.key(channel, publish_at)] = {
                "channel": channel, "publish_at": local.isoformat() if local else None, "sha256": fingerprint,
                "test_id": publish_at if local is None else None,
                "title": title, "clips": clips, "started_at": now, "status": "uploading",
            }
            self.save(records)
        return None

    def complete(self, channel, publish_at, video_id):
        with LOCK, storage_lock(self.path):
            records = self.load()
            record = records[self.key(channel, publish_at)]
            is_test = isinstance(publish_at, str)
            record.update(video_id=video_id, status="uploaded" if is_test else "scheduled", privacy_status="unlisted" if is_test else "private", completed_at=time.time(),
                          url=f"https://www.youtube.com/shorts/{video_id}")
            self.save(records)

