"""
Transform Webinar — Flask backend
Serves gym.html and sends registration confirmation emails via Gmail SMTP.

Run:
    pip install flask
    python app.py

Then open http://localhost:5000
"""

import smtplib
import os
import json
import html
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import Flask, send_file, request, jsonify

# ── CONFIG ────────────────────────────────────────────────────────────────────
GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS", "fitandfuel01@gmail.com")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS", "rycs oaoi jsps dolt")
FROM_DISPLAY   = os.environ.get("FROM_DISPLAY", "Transform Team")
BUSINESS_TZ    = os.environ.get("BUSINESS_TIMEZONE", "Asia/Kolkata")
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

HTML_PATH = Path(__file__).parent / "gym.html"
BANNER_PATH = Path(__file__).parent / "banner.png"


def clean(value):
    """Escape user-provided values before rendering them into emails."""
    return html.escape(str(value or "").strip(), quote=True)


def get_zone(timezone_name, fallback="UTC"):
    try:
        return ZoneInfo(timezone_name or fallback)
    except ZoneInfoNotFoundError:
        return ZoneInfo(fallback)


def format_now(timezone_name):
    local_time = datetime.now(timezone.utc).astimezone(get_zone(timezone_name))
    return local_time.strftime("%Y-%m-%d %H:%M:%S %Z")


# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the landing page."""
    return send_file(HTML_PATH)


@app.route("/banner.png")
def banner():
    """Serve the landing page hero image in local and Vercel environments."""
    return send_file(BANNER_PATH)


@app.route("/register", methods=["POST"])
def register():
    """
    Receive registration JSON and send a confirmation email to the registrant.
    Also sends a notification copy to the business inbox.

    Expected JSON body:
        { "first": "...", "last": "...", "email": "...", "goal": "...", "session": "..." }
    """
    data    = request.get_json(force=True, silent=True) or {}
    first   = data.get("first",   "").strip()
    last    = data.get("last",    "").strip()
    email   = data.get("email",   "").strip()
    goal    = data.get("goal",    "").strip()
    session = data.get("session", "").strip()
    user_tz = data.get("timezone", "UTC").strip() or "UTC"

    if not all([first, last, email, goal, session]):
        return jsonify({"ok": False, "error": "Missing required fields"}), 400

    full_name = f"{first} {last}"
    safe_first = clean(first)
    safe_full_name = clean(full_name)
    safe_email = clean(email)
    safe_goal = clean(goal)
    safe_session = clean(session)
    safe_user_tz = clean(user_tz)

    try:
        # ── Build confirmation email to the registrant ───────────────────────
        registrant_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>You're registered - FitAndFuel Free Webinar</title>
<style>
  body {{ margin:0; padding:0; background-color:#ffffff; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; color:#1d1d1f; }}
  table {{ border-spacing:0; border-collapse:collapse; }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;color:#1d1d1f;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;padding:40px 20px;">
  <tr>
    <td align="center">
      <table width="100%" max-width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

        <!-- Header Logo -->
        <tr>
          <td align="left" style="padding-bottom:32px;">
            <div style="font-size:24px;font-weight:600;letter-spacing:-0.5px;color:#1d1d1f;">FitAndFuel</div>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td align="left" style="padding-bottom:24px;">
            <p style="margin:0;font-size:17px;font-weight:400;line-height:1.47059;color:#1d1d1f;">
              Dear {safe_first},
            </p>
          </td>
        </tr>

        <!-- Message -->
        <tr>
          <td align="left" style="padding-bottom:32px;">
            <p style="margin:0;font-size:17px;font-weight:400;line-height:1.47059;color:#1d1d1f;">
              You have selected {safe_email} for your FitAndFuel webinar registration. Your seat is reserved for the session below:
            </p>
          </td>
        </tr>

        <!-- Session detail card -->
        <tr>
          <td style="padding-bottom:40px;">
            <table cellpadding="0" cellspacing="0" width="100%" style="border:1px solid #d2d2d7;border-radius:12px;overflow:hidden;">
              <tr>
                <td style="padding:20px 24px;border-bottom:1px solid #d2d2d7;">
                  <div style="font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Session</div>
                  <div style="font-size:17px;font-weight:600;color:#1d1d1f;">{safe_session}</div>
                </td>
              </tr>
              <tr>
                <td style="padding:20px 24px;border-bottom:1px solid #d2d2d7;">
                  <div style="font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Your goal</div>
                  <div style="font-size:17px;font-weight:600;color:#1d1d1f;">{safe_goal}</div>
                </td>
              </tr>
              <tr>
                <td style="padding:20px 24px;">
                  <div style="font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Note</div>
                  <div style="font-size:17px;font-weight:600;color:#1d1d1f;">A Zoom link will be sent to your address 1 hour before the session.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Divider -->
        <tr>
          <td align="center" style="padding-bottom:24px;">
            <hr style="border:none;border-top:1px solid #d2d2d7;margin:0;" />
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td align="left">
            <p style="margin:0;font-size:12px;font-weight:400;line-height:1.33333;color:#86868b;">
              Wondering why you got this email?<br>
              It's sent when someone registers for a FitAndFuel webinar. If you didn't sign up, you can safely ignore this message. No further emails will be sent.
            </p>
            <p style="margin:16px 0 0;font-size:12px;font-weight:400;line-height:1.33333;color:#86868b;">
              FitAndFuel Support
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""

        # ── Build internal notification to business inbox ──────────────────
        sent_at = format_now(BUSINESS_TZ)
        sent_at_utc = format_now("UTC")
        notify_html = f"""
<html><body style="font-family:sans-serif;color:#1C1C1E;padding:20px;">
  <h2 style="color:#007AFF;">New Webinar Registration</h2>
  <table cellpadding="8" cellspacing="0" style="border-collapse:collapse;width:100%;max-width:480px;">
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Name</td><td style="border-bottom:1px solid #E5E5EA;">{safe_full_name}</td></tr>
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Email</td><td style="border-bottom:1px solid #E5E5EA;">{safe_email}</td></tr>
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Goal</td><td style="border-bottom:1px solid #E5E5EA;">{safe_goal}</td></tr>
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Session</td><td style="border-bottom:1px solid #E5E5EA;">{safe_session}</td></tr>
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Visitor timezone</td><td style="border-bottom:1px solid #E5E5EA;">{safe_user_tz}</td></tr>
    <tr><td style="font-weight:600;border-bottom:1px solid #E5E5EA;">Sent at</td><td style="border-bottom:1px solid #E5E5EA;">{sent_at}</td></tr>
    <tr><td style="font-weight:600;">UTC</td><td>{sent_at_utc}</td></tr>
  </table>
</body></html>
"""

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            if not GMAIL_ADDRESS or not GMAIL_APP_PASS:
                raise RuntimeError("Missing GMAIL_ADDRESS or GMAIL_APP_PASS environment variable")

            smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASS.replace(" ", ""))

            # 1. Confirmation to registrant
            msg1 = MIMEMultipart("alternative")
            msg1["Subject"] = "You're registered - FitAndFuel Free Webinar"
            msg1["From"]    = f"{FROM_DISPLAY} <{GMAIL_ADDRESS}>"
            msg1["To"]      = email
            msg1.attach(MIMEText(registrant_html, "html"))
            smtp.sendmail(GMAIL_ADDRESS, email, msg1.as_string())

            # 2. Internal notification
            msg2 = MIMEMultipart("alternative")
            msg2["Subject"] = f"[FitAndFuel] New registration - {full_name}"
            msg2["From"]    = GMAIL_ADDRESS
            msg2["To"]      = GMAIL_ADDRESS
            msg2.attach(MIMEText(notify_html, "html"))
            smtp.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg2.as_string())

        sent_at = format_now(BUSINESS_TZ)
        print(f"[register] Emails sent for {full_name} <{email}> at {sent_at}")
        return jsonify({"ok": True})

    except smtplib.SMTPAuthenticationError:
        print("[register] SMTP authentication failed - check app password")
        return jsonify({"ok": False, "error": "Email auth failed"}), 500
    except Exception as exc:
        print(f"[register] Error: {exc}")
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("─" * 60)
    print("  Transform Webinar — Backend")
    print(f"  Serving:  http://{host}:{port}")
    print(f"  Gmail:    {GMAIL_ADDRESS}")
    print("─" * 60)
    app.run(debug=True, host=host, port=port)
