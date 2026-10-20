"""Public information pages used by the Google OAuth consent screen."""

from flask import Blueprint, Response


branding = Blueprint("branding", __name__)
APP_PROFILES = {
    "traderfx": {
        "name": "TraderFX Channel 3 Automation",
        "support_email": "topxcoupon@gmail.com",
        "base_path": "",
        "channel_note": "",
    },
    "apex": {
        "name": "Pocket Option YouTube Automation",
        "support_email": "neetud252@gmail.com",
        "base_path": "/apex",
        "channel_note": "<p>For the Apex Trader YouTube channel.</p>",
    },
}


def information_page(title, body, profile="traderfx"):
    settings = APP_PROFILES[profile]
    app_name = settings["name"]
    support_email = settings["support_email"]
    base_path = settings["base_path"]
    body = body.format(
        app_name=app_name,
        support_email=support_email,
        base_path=base_path,
        channel_note=settings["channel_note"],
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | {app_name}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ margin: 0; background: #f6f8fb; color: #17243a;
      font: 17px/1.65 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 780px; margin: 48px auto; padding: 36px;
      background: white; border: 1px solid #dce3ee; border-radius: 16px; }}
    nav {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 22px 0 32px; }}
    a {{ color: #174fa2; text-underline-offset: 3px; }}
    h1 {{ font-size: clamp(28px, 5vw, 38px); line-height: 1.2; }}
    h2 {{ font-size: 23px; margin-top: 32px; }}
    .brand {{ color: #52647c; font-size: 14px; font-weight: 650; }}
    .date {{ color: #52647c; font-size: 14px; }}
    footer {{ border-top: 1px solid #dce3ee; margin-top: 32px; padding-top: 20px; }}
    @media (max-width: 600px) {{ main {{ margin: 16px; padding: 24px; }} }}
  </style>
</head>
<body>
<main>
  <div class="brand">{app_name}</div>
  <nav aria-label="Information pages">
    <a href="{base_path}/about">Home</a>
    <a href="{base_path}/privacy">Privacy policy</a>
    <a href="{base_path}/terms">Terms of service</a>
  </nav>
  {body}
  <footer>Support: <a href="mailto:{support_email}">{support_email}</a></footer>
</main>
</body>
</html>"""
    return Response(html, content_type="text/html; charset=utf-8")


@branding.get("/about")
@branding.get("/apex/about", defaults={"profile": "apex"})
def about(profile="traderfx"):
    return information_page("Home", """
<h1>{app_name}</h1>
{channel_note}
<p>A tool for the channel operator to prepare, upload, and schedule videos
on an authorised YouTube channel. It runs as part of the Pocket Option
YouTube Automation service.</p>
<h2>What the app does</h2>
<ul>
  <li>Connects the operator's YouTube channel using Google OAuth.</li>
  <li>Checks channel identity and the status of uploaded videos.</li>
  <li>Uploads generated videos, sets thumbnails when supported, and schedules publication.</li>
  <li>Keeps upload records and reports automation status to the operator.</li>
</ul>
<h2>Google account access</h2>
<p>Google asks for permission before a channel is connected. The service
stores an offline authorisation token so scheduled work can run without
repeated sign-in. Access can be revoked through your Google Account.</p>
<p>This is an operator-managed tool for authorised channels. It is not a
public account-registration service.</p>
<p>Read the <a href="{base_path}/privacy">privacy policy</a> for data use, storage,
and removal information, and the <a href="{base_path}/terms">terms of service</a>
for conditions of use.</p>
""", profile)


@branding.get("/privacy")
@branding.get("/apex/privacy", defaults={"profile": "apex"})
def privacy(profile="traderfx"):
    return information_page("Privacy policy", """
<h1>Privacy policy</h1>
<p class="date">Effective 20 October 2026</p>
<p>This policy covers the YouTube channel integration of {app_name},
operated as part of the Pocket Option YouTube Automation service.
It describes this integration's handling of Google user data.</p>
<h2>Information accessed and stored</h2>
<p>With your Google authorisation, the integration accesses the selected
channel's identifier, name, and profile information; video identifiers,
metadata, publication schedules, and upload status; and the permissions
needed to upload videos and manage supported thumbnails.</p>
<p>The service stores OAuth access and refresh tokens, granted scopes,
token-expiry information, channel metadata, upload receipts, scheduling
records, and operational status. Google handles sign-in; the integration
does not ask for or store your Google password. A session cookie is used
to validate the OAuth connection flow.</p>
<h2>How information is used</h2>
<p>These records let the operator connect the correct channel, run scheduled
uploads, check publication status, refresh authorisation, and avoid duplicate
uploads. Google user data is used for these channel features, not for
targeted advertising or training AI models, and is not sold.</p>
<p>The integration's use and transfer of information received from Google
APIs adheres to the
<a href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</a>,
including its Limited Use requirements.</p>
<h2>Storage and services involved</h2>
<p>The application runs on Railway. Tokens and channel and upload records
are stored in the service's persistent storage. Google and YouTube receive
authorised API requests, uploaded videos, thumbnails, and associated
metadata. When operator notifications are enabled, automation status and
video links may be sent to the configured administrator through Telegram.</p>
<p>Content-generation and voice services process prompts and narration text
to produce video content. The channel integration does not send Google
OAuth tokens to those services. The connection dashboard displays channel
names, channel identifiers, and connection status to visitors who can
access that dashboard.</p>
<h2>Retention and removal</h2>
<p>Tokens and operational records remain in service storage until removed
by the operator. Temporary rendered media is normally removed after the
upload attempt. Removing Google access does not automatically erase local
upload records or remove videos already uploaded to YouTube.</p>
<p>You can revoke access in your
<a href="https://myaccount.google.com/connections">Google Account connections</a>.
To request removal of stored tokens or channel data, contact
<a href="mailto:{support_email}">{support_email}</a> and identify
the channel concerned. Do not send passwords or OAuth tokens. Videos
already on YouTube can be managed in YouTube Studio.</p>
<h2>Questions and changes</h2>
<p>Contact the support address below with privacy questions. Updates to
this policy will be published on this page with a revised effective date.</p>
""", profile)


@branding.get("/terms")
@branding.get("/apex/terms", defaults={"profile": "apex"})
def terms(profile="traderfx"):
    return information_page("Terms of service", """
<h1>Terms of service</h1>
<p class="date">Effective 20 October 2026</p>
<h2>Purpose and authorised use</h2>
<p>{app_name} is an operator-managed video upload and
scheduling tool. Use it only for YouTube channels you own or are authorised
to manage. It is not a public account-registration service.</p>
<h2>Uploads and scheduling</h2>
<p>Connecting a channel allows the configured automation to upload videos
and related metadata, apply supported thumbnails, and schedule publication.
The operator is responsible for reviewing content, owning the necessary
rights, and choosing appropriate schedules and visibility settings.</p>
<p>The service uses YouTube API Services. Use of YouTube is subject to the
<a href="https://www.youtube.com/t/terms">YouTube Terms of Service</a>
and applicable YouTube policies. The automation is not affiliated with
or endorsed by Google or YouTube.</p>
<h2>Availability and stopping access</h2>
<p>Uploads and publication depend on hosting availability, API quotas,
valid authorisation, and YouTube processing. Successful upload or exact
publication timing is not guaranteed.</p>
<p>The operator can pause the automation or revoke its Google access.
Revoking access stops future authorised API operations but does not
automatically cancel videos already scheduled on YouTube; manage those
videos in YouTube Studio.</p>
<h2>Privacy and support</h2>
<p>The <a href="{base_path}/privacy">privacy policy</a> explains the integration's data
handling and how to request removal of stored channel information.
For support, contact <a href="mailto:{support_email}">{support_email}</a>.</p>
""", profile)
