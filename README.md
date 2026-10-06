# Pocket Option YouTube Automation

New uploads on both channels extract the frame at 00:02 from the final video
and submit it as a JPEG thumbnail. Temporary images are removed after upload.
Transient thumbnail errors are retried without reuploading the video. Results
are stored in `data/thumbnail_<video_id>.json` and scheduled buffer records.
If YouTube rejects a custom Shorts thumbnail, the video stays scheduled with
YouTube's default thumbnail, and the failure is logged. Existing uploads are
unchanged.

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

## Telegram gift and trading-access flow

The existing Telegram admin bot also supports public onboarding:

1. The user opens the bot and follows the account-registration link.
2. The user submits a trading-account UID.
3. The UID is verified by the configured provider API, or sent to the admin for
   manual approval when no API is configured.
4. The verified user sees **Claim Free Money Management Sheet**.
5. After the user confirms receipt of the spreadsheet, **Start Trading** checks
   the required deposit.
6. A verified deposit unlocks the configured trading-access link.

User progress and the gift's Telegram file ID are stored in
`/app/data/telegram_user_access.json` on the existing Railway volume. One UID
cannot be claimed by multiple Telegram accounts.

Upload or replace the Excel gift by sending the `.xlsx` or `.xls` document to
the Telegram bot from the configured admin account, with `/setgift` in the file
caption. Telegram hosts the document and the bot stores its reusable `file_id`;
the spreadsheet does not need to be committed to GitHub or uploaded to Railway.
Use `/users` or the **USERS** dashboard button to view onboarding totals.

Configure these Railway variables:

- `ACCOUNT_REGISTRATION_URL`: affiliate registration/deposit URL shown to users.
- `REQUIRED_DEPOSIT_AMOUNT`: minimum verified deposit amount.
- `DEPOSIT_CURRENCY`: display currency such as `USD`.
- `TRADING_ACCESS_URL`: private group, dashboard, or onboarding URL granted after verification.
- `SUPPORT_USERNAME`: Telegram username without `@` (optional).
- `UID_VERIFY_URL`: server-side UID verification endpoint (optional).
- `DEPOSIT_VERIFY_URL`: server-side deposit verification endpoint (optional).
- `AFFILIATE_API_KEY`: bearer/API key sent only to the verification endpoints (optional).

Verification endpoints receive JSON. UID verification receives `uid` and
`telegram_user_id`. Deposit verification also receives `required_amount` and
`currency`. A response can approve with `verified: true`,
`account_verified: true`, `deposit_verified: true`, or a `status` of
`verified`, `approved`, or `success`. Deposit responses may return
`deposit_amount`, `total_deposit`, or `amount`. When an endpoint is omitted,
the admin receives Approve and Reject buttons inside Telegram.
