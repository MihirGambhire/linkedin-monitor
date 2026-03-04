"""
Email sender module — sends the LinkedIn monitor digest via Gmail SMTP.

Sends a rich HTML email with:
- Summary table of all discovered posts
- Inline screenshots as image attachments
- Direct clickable links to each LinkedIn post
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import Dict, List, Optional

from .config import EmailConfig
from .search import SearchResult

logger = logging.getLogger(__name__)


def _build_html_body(
    results: Dict[str, List[SearchResult]],
    screenshots: Dict[str, Optional[str]],
) -> tuple:
    """
    Build HTML email body with embedded screenshots.

    Returns:
        Tuple of (html_body, list of (cid, filepath) for inline images)
    """
    total_posts = sum(len(posts) for posts in results.values())
    now = datetime.utcnow().strftime("%B %d, %Y")

    inline_images = []  # (content_id, filepath)

    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #0077B5, #00A0DC);
                color: white;
                padding: 24px 32px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 22px;
                font-weight: 600;
            }}
            .header p {{
                margin: 8px 0 0;
                opacity: 0.9;
                font-size: 14px;
            }}
            .content {{
                padding: 24px 32px;
            }}
            .category {{
                margin-bottom: 32px;
            }}
            .category h2 {{
                color: #0077B5;
                font-size: 18px;
                border-bottom: 2px solid #e8e8e8;
                padding-bottom: 8px;
                margin-bottom: 16px;
            }}
            .post-card {{
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                margin-bottom: 16px;
                overflow: hidden;
            }}
            .post-info {{
                padding: 16px;
            }}
            .post-title {{
                font-size: 15px;
                font-weight: 600;
                color: #333;
                margin: 0 0 8px;
            }}
            .post-title a {{
                color: #0077B5;
                text-decoration: none;
            }}
            .post-title a:hover {{
                text-decoration: underline;
            }}
            .post-snippet {{
                font-size: 13px;
                color: #666;
                line-height: 1.5;
                margin: 0;
            }}
            .post-screenshot {{
                padding: 0 16px 16px;
            }}
            .post-screenshot img {{
                width: 100%;
                border-radius: 4px;
                border: 1px solid #e8e8e8;
            }}
            .footer {{
                background: #f9f9f9;
                padding: 16px 32px;
                text-align: center;
                color: #999;
                font-size: 12px;
            }}
            .badge {{
                display: inline-block;
                background: #e7f3ff;
                color: #0077B5;
                padding: 2px 10px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 8px;
            }}
            .no-results {{
                color: #999;
                font-style: italic;
                padding: 8px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 LinkedIn Keyword Monitor</h1>
                <p>ADOR Digatron — {total_posts} posts found on {now}</p>
            </div>
            <div class="content">
    """

    if total_posts == 0:
        html += """
            <p class="no-results">
                No new LinkedIn posts found matching your keywords this period.
                This can happen when posts are not publicly visible or 
                the search didn't return results for the current time window.
            </p>
        """
    else:
        img_idx = 0
        for category, posts in results.items():
            html += f"""
                <div class="category">
                    <h2>{category}</h2>
            """
            if not posts:
                html += '<p class="no-results">No posts found in this category.</p>'
            else:
                for post in posts:
                    html += f"""
                    <div class="post-card">
                        <div class="post-info">
                            <span class="badge">{category}</span>
                            <p class="post-title">
                                <a href="{post.url}" target="_blank">
                                    {post.title}
                                </a>
                            </p>
                            <p class="post-snippet">{post.snippet}</p>
                        </div>
                    """

                    # Add inline screenshot if available
                    screenshot_path = screenshots.get(post.url)
                    if screenshot_path and os.path.exists(screenshot_path):
                        cid = f"screenshot_{img_idx}"
                        inline_images.append((cid, screenshot_path))
                        html += f"""
                        <div class="post-screenshot">
                            <img src="cid:{cid}" alt="Post screenshot" />
                        </div>
                        """
                        img_idx += 1

                    html += "</div>"  # close post-card

            html += "</div>"  # close category

    html += """
            </div>
            <div class="footer">
                Automated by LinkedIn Keyword Monitor for ADOR Digatron<br/>
                Powered by GitHub Actions • 
                <a href="https://adordigatron.com" style="color: #0077B5;">
                    adordigatron.com
                </a>
            </div>
        </div>
    </body>
    </html>
    """

    return html, inline_images


def send_email(
    results: Dict[str, List[SearchResult]],
    screenshots: Dict[str, Optional[str]],
    config: Optional[EmailConfig] = None,
) -> bool:
    """
    Send the LinkedIn monitor digest email.

    Args:
        results: Dict of category -> list of SearchResult
        screenshots: Dict of URL -> screenshot filepath
        config: Email configuration. If None, uses defaults (env vars).

    Returns:
        True if email was sent successfully, False otherwise
    """
    if config is None:
        config = EmailConfig()

    if not config.sender_email or not config.sender_password:
        logger.error(
            "Email credentials not configured. "
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables."
        )
        return False

    if not config.recipient_email:
        logger.error("RECIPIENT_EMAIL not set.")
        return False

    total = sum(len(p) for p in results.values())
    today = datetime.utcnow().strftime("%Y-%m-%d")
    subject = f"{config.subject_prefix} — {total} posts found ({today})"

    # Build message
    msg = MIMEMultipart("related")
    msg["From"] = config.sender_email
    msg["To"] = config.recipient_email
    msg["Subject"] = subject

    # Build HTML body
    html_body, inline_images = _build_html_body(results, screenshots)
    msg.attach(MIMEText(html_body, "html"))

    # Attach inline screenshots
    for cid, filepath in inline_images:
        try:
            with open(filepath, "rb") as f:
                img = MIMEImage(f.read(), _subtype="png")
                img.add_header("Content-ID", f"<{cid}>")
                img.add_header(
                    "Content-Disposition", "inline", filename=os.path.basename(filepath)
                )
                msg.attach(img)
        except Exception as e:
            logger.warning(f"Could not attach screenshot {filepath}: {e}")

    # Also attach screenshots as regular attachments for download
    for cid, filepath in inline_images:
        try:
            with open(filepath, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=os.path.basename(filepath),
                )
                msg.attach(attachment)
        except Exception:
            pass

    # Send via SMTP
    try:
        logger.info(f"Sending email to {config.recipient_email}...")
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.sender_email, config.sender_password)
            server.sendmail(
                config.sender_email,
                config.recipient_email,
                msg.as_string(),
            )
        logger.info("Email sent successfully! ✅")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. "
            "Make sure you're using an App Password (not your regular password). "
            "Enable 2FA on your Google account and create an App Password at: "
            "https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
