# Pocket Option YouTube Automation

Automated YouTube Shorts generator and uploader for the Pocket Option AI Bot.

Planned workflow:
1. Generate unique Short topics and scripts
2. Generate voiceovers
3. Select varied footage
4. Render vertical videos with FFmpeg
5. Generate titles and descriptions
6. Upload or schedule Shorts through the YouTube API
7. Track content history to reduce repetition

Secrets will be stored in Railway environment variables, not in GitHub.
# Two-channel schedule

Every day at 22:00 Asia/Kolkata, the scheduler prepares the next calendar day's
Shorts. The original channel retains 10:00 and 18:00; @goplustrader uses 00:00
and 18:00. Midnight means the start of tomorrow, two hours after creation.

Connect the second Google account at `/authorize?channel=goplustrader` after
deploying this version. Select the account owning @goplustrader. The callback
checks its YouTube channel ID against the handle before saving a separate
`youtube_token_goplustrader.json`. The original token and old buffer records
remain valid. If the Google OAuth app is in testing mode, the new Google account
must be added as a test user in that OAuth project's consent configuration.

The new channel participates automatically once authorized. Each slot creates
its own script, voiceover, and rendered video using the existing voice/music
settings. Both channels share `content_history.json`, including duplicate and
similarity rejection. An unreadable history stops creation rather than permitting
repeated scripts. The buffer is keyed by channel and publishing timestamp, so
both 18:00 slots coexist. Legacy records belong to the original channel.

`/health` reports each channel's connection, schedule, and missing slots.
Manual recovery accepts `/fill-required?channel=goplustrader`; tomorrow-only
preparation accepts `/fill-buffer?channel=goplustrader`. Recovery skips past
slots. Keep one scheduler process and persistent `/app/data` storage, as before.
OAuth sessions expire after ten minutes or an application restart.

Tests: `python -m unittest discover -s tests -v` (application dependencies needed).
Tests disable background threads and use temporary storage and mocked APIs;
they do not generate paid audio or upload videos.
