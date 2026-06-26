"""
Email delivery via SMTP with a first-class Gmail preset (EMAIL_SERVICE=gmail).

Set EMAIL_SERVICE=smtp and SMTP_HOST for non-Google providers.
Environment is read at send time so Flask .env merges apply correctly.
"""

import os
import smtplib
import socket
import ssl
import logging
from datetime import datetime
from pathlib import Path
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import formataddr, formatdate, make_msgid, parseaddr

from dotenv import dotenv_values

logger = logging.getLogger(__name__)


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_ROOT.parent
_BACKEND_ENV_FILE = _BACKEND_ROOT / '.env'
_REPO_ENV_FILE = _REPO_ROOT / '.env'


_PLACEHOLDER_HINTS = (
    'your_email',
    'your-email',
    'your_email@gmail.com',
    'your-email@gmail.com',
    'your-app-password',
    'your_app_password',
    'example.com',
    'your-domain.com',
    'replace-me',
    'replace_with',
    'placeholder',
    'dummy',
)


def _is_placeholder_env_value(key: str, value: str) -> bool:
    """Return True when an env value is clearly a sample/placeholder.

    This is intentionally conservative for email-specific settings so a real
    Gmail credential in one .env file is not overridden by placeholders in
    another .env file or by stale process env values.
    """
    if value is None:
        return True

    v = str(value).strip()
    if not v:
        return True

    lowered = v.lower()
    email_keys = {
        'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_PASS', 'EMAIL_FROM',
        'SMTP_HOST', 'SMTP_EHLO_HOSTNAME', 'EMAIL_HOST',
    }
    if key in email_keys:
        if any(hint in lowered for hint in _PLACEHOLDER_HINTS):
            return True
        if 'your' in lowered and ('password' in lowered or 'email' in lowered):
            return True
    return False


def _merged_runtime_env() -> dict:
    """Read repo/backend .env files on every call, then overlay process env values.

    File values win over stale process values so edits to .env take effect
    without requiring a server restart.
    """
    merged: dict = {}

    for env_file in (_REPO_ENV_FILE, _BACKEND_ENV_FILE):
        if not env_file.exists():
            continue
        try:
            values = dotenv_values(env_file)
        except Exception:
            values = {}

        for key, value in values.items():
            if not key or key.startswith('\ufeff'):
                continue
            if _is_placeholder_env_value(key, value):
                continue
            merged[key] = str(value).strip()

    for key, value in os.environ.items():
        if not key or key.startswith('\ufeff'):
            continue
        value_str = str(value).strip()
        if value_str and key not in merged and not _is_placeholder_env_value(key, value_str):
            merged[key] = value_str

    return merged


def _env_value(name: str, default=None):
    env = _merged_runtime_env()
    return env.get(name, default)


def _read_int_env(name: str, default: int) -> int:
    try:
        return int(_env_value(name, str(default)))
    except ValueError:
        return default


def _read_int_env_any(names: tuple[str, ...], default: int) -> int:
    for name in names:
        raw = _env_value(name)
        if raw is not None and str(raw).strip() != '':
            try:
                return int(str(raw).strip())
            except ValueError:
                continue
    return default


def _read_bool_env(name: str, default: bool) -> bool:
    raw = _env_value(name)
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if value in ('0', 'false', 'no', 'n', 'off'):
        return False
    return default


def _env_explicitly_nonempty(*names: str) -> bool:
    for name in names:
        raw = _env_value(name)
        if raw is not None and str(raw).strip():
            return True
    return False


def resolve_email_provider() -> str:
    """
    EMAIL_SERVICE / EMAIL_PROVIDER presets:
      gmail — Google personal (@gmail.com) or Workspace; defaults to smtp.gmail.com
      smtp  — arbitrary SMTP server; require SMTP_HOST or EMAIL_HOST
    """
    raw = (
        _env_value('EMAIL_SERVICE')
        or _env_value('EMAIL_PROVIDER')
        or 'gmail'
    ).strip().lower()
    if raw in ('gmail', 'google', 'gsuite', 'googlemail', ''):
        return 'gmail'
    if raw in ('smtp', 'custom', 'generic'):
        return 'smtp'
    return 'smtp'


def _email_settings() -> dict:
    """Fresh env snapshot for every send (Gmail SMTP and generic SMTP)."""
    base = (_env_value('FRONTEND_BASE_URL') or 'http://localhost:5173').rstrip('/')
    provider = resolve_email_provider()

    explicit_host = (_env_value('SMTP_HOST') or _env_value('EMAIL_HOST') or '').strip()
    if explicit_host:
        smtp_host = explicit_host
    elif provider == 'gmail':
        smtp_host = 'smtp.gmail.com'
    else:
        smtp_host = ''

    smtp_port = _read_int_env_any(('SMTP_PORT', 'EMAIL_PORT'), 587)
    use_tls_default = smtp_port != 465
    # Gmail on 587 requires STARTTLS; 465 uses implicit TLS (SMTP_SSL branch).
    if provider == 'gmail' and smtp_port == 587 and not _env_explicitly_nonempty('EMAIL_USE_TLS'):
        smtp_use_tls = True
    else:
        smtp_use_tls = _read_bool_env('EMAIL_USE_TLS', use_tls_default)

    return {
        'email_provider': provider,
        'email_user': (_env_value('EMAIL_USER') or '').strip(),
        # Support both EMAIL_PASSWORD and EMAIL_PASS for compatibility.
        'email_password_raw': (_env_value('EMAIL_PASSWORD') or _env_value('EMAIL_PASS') or '').strip(),
        'email_from': (_env_value('EMAIL_FROM') or '').strip(),
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'smtp_use_tls': smtp_use_tls,
        'frontend_base_url': base,
        'token_expiry_hours': _read_int_env('EMAIL_TOKEN_EXPIRY_HOURS', 24),
    }


def _normalize_app_password(raw: str) -> str:
    raw = (raw or '').strip().strip('"').strip("'")
    return ''.join(raw.split()) if raw else ''


def _looks_like_placeholder(value: str) -> bool:
    v = (value or '').strip().lower()
    if not v:
        return True
    return (
        'your_email' in v
        or 'example.com' in v
        or v in {'your-app-password', 'your_app_password', 'your-email@gmail.com'}
        or ('your' in v and 'password' in v)
    )


def _ehlo_hostname() -> str:
    h = (_env_value('SMTP_EHLO_HOSTNAME') or '').strip()
    if h:
        return h
    fqdn = socket.getfqdn()
    if fqdn and fqdn not in ('localhost', '127.0.0.1'):
        return fqdn
    return 'plpg-client.local'


def get_email_config_status() -> dict:
    """
    Return configuration readiness and missing/invalid keys for diagnostics.
    """
    s = _email_settings()
    user = (s.get('email_user') or '').strip()
    password = _normalize_app_password(s.get('email_password_raw') or '')
    host = (s.get('smtp_host') or '').strip()
    port = int(s.get('smtp_port') or 0)
    provider = s.get('email_provider') or resolve_email_provider()

    issues: list[str] = []
    if not user or _looks_like_placeholder(user):
        issues.append('EMAIL_USER')
    if not password or _looks_like_placeholder(password):
        issues.append('EMAIL_PASSWORD')
    if not host:
        issues.append('SMTP_HOST/EMAIL_HOST')
    if port <= 0:
        issues.append('SMTP_PORT/EMAIL_PORT')

    return {
        'configured': len(issues) == 0,
        'issues': issues,
        'provider': provider,
        'host': host,
        'port': port,
        'use_tls': bool(s.get('smtp_use_tls', True)),
    }


class EmailService:
    """Email service class for sending emails"""
    
    _transporter = None
    # Human-readable last error for diagnostics (set when a send fails)
    _last_error: str | None = None
    
    @staticmethod
    def _smtp_from_header() -> str:
        """
        Gmail rejects (or drops) mail if the visible From address does not match
        the authenticated mailbox. Normalize display name + envelope identity.
        """
        s = _email_settings()
        user = s['email_user']
        raw = (s['email_from'] or user).strip()
        name, addr = parseaddr(raw)
        if not addr or addr.lower() != user.lower():
            if name and name.strip():
                return formataddr((name.strip(), user))
            return user
        return raw if raw else user

    @staticmethod
    def _get_transporter():
        """SMTP connection parameters from environment."""
        s = _email_settings()
        status = get_email_config_status()
        if not status['configured']:
            print('Email service not configured (missing EMAIL_USER or EMAIL_PASSWORD)')
            return None
        user = s['email_user']
        password = _normalize_app_password(s['email_password_raw'])

        return {
            'host': s['smtp_host'],
            'port': int(s['smtp_port']),
            'user': user,
            'password': password,
            'use_tls': bool(s['smtp_use_tls']),
        }

    @staticmethod
    def get_last_error() -> str | None:
        """Return the last human-readable SMTP/error message (or None)."""
        return EmailService._last_error
    
    @staticmethod
    def send_email(to: str, subject: str, html_content: str, text_content: str = None) -> bool:
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            
        Returns:
            True if sent successfully
        """
        transporter = EmailService._get_transporter()
        if not transporter:
            logger.warning('Email service not configured')
            return False

        smtp_user = (transporter['user'] or '').strip()
        smtp_password = transporter['password']
        host = transporter['host']
        port = int(transporter['port'])
        use_tls = bool(transporter.get('use_tls', True))
        local_hostname = _ehlo_hostname()
        to_addr = (to or '').strip()
        if not host:
            logger.error('SMTP host is empty; set SMTP_HOST or EMAIL_HOST')
            return False
        if not to_addr:
            logger.error('Recipient email is empty')
            return False

        try:
            # Clear last error before attempting a send
            EmailService._last_error = None
            msg = EmailMessage(policy=SMTP_POLICY)
            msg['Subject'] = subject
            msg['From'] = EmailService._smtp_from_header()
            msg['To'] = to_addr
            msg['Date'] = formatdate(localtime=True)
            mail_domain = smtp_user.split('@', 1)[-1] if '@' in smtp_user else 'localhost'
            msg['Message-ID'] = make_msgid(domain=mail_domain)
            msg['Reply-To'] = smtp_user

            plain = (text_content or 'Open this message in an HTML-capable email app to view your PLPG link.').strip()
            msg.set_content(plain, charset='utf-8')
            msg.add_alternative(html_content, subtype='html', charset='utf-8')

            ctx = ssl.create_default_context()
            to_addrs = [to_addr]
            smtp_debug = _read_bool_env('SMTP_DEBUG', False)

            if port == 465:
                with smtplib.SMTP_SSL(
                    host, port, context=ctx, timeout=30, local_hostname=local_hostname
                ) as server:
                    if smtp_debug:
                        server.set_debuglevel(1)
                    server.login(smtp_user, smtp_password)
                    refused = server.send_message(msg, from_addr=smtp_user, to_addrs=to_addrs)
            else:
                with smtplib.SMTP(
                    host, port, timeout=30, local_hostname=local_hostname
                ) as server:
                    if smtp_debug:
                        server.set_debuglevel(1)
                    server.ehlo()
                    if use_tls:
                        server.starttls(context=ctx)
                        server.ehlo()
                    server.login(smtp_user, smtp_password)
                    refused = server.send_message(msg, from_addr=smtp_user, to_addrs=to_addrs)

            if refused:
                err = f'SMTP server refused delivery for: {refused}'
                logger.error(err)
                EmailService._last_error = err
                return False

            logger.info(
                'Email sent via SMTP (provider=%s) to %s (from %s)',
                resolve_email_provider(),
                to_addr,
                smtp_user,
            )
            return True

        except smtplib.SMTPAuthenticationError as e:
            msg = f'SMTP Authentication failed for {smtp_user}: {e}'
            logger.error(msg)
            EmailService._last_error = msg
            return False
        except smtplib.SMTPException as e:
            msg = f'SMTP error sending to {to_addr}: {e}'
            logger.error(msg)
            EmailService._last_error = msg
            return False
        except Exception as e:
            msg = f'Unexpected error sending email to {to_addr}: {e}'
            logger.error(msg)
            EmailService._last_error = msg
            return False
    
    @staticmethod
    def send_verification_email(to: str, token: str, user_name: str = None) -> bool:
        """
        Send email verification email
        
        Args:
            to: Recipient email address
            token: Verification token
            user_name: User's name
            
        Returns:
            True if sent successfully
        """
        s = _email_settings()
        verification_link = f"{s['frontend_base_url']}/verify-email?token={token}"

        html_content = EmailService._get_verification_email_html(
            user_name or 'User',
            verification_link,
            s['token_expiry_hours'],
        )

        text_content = f"""
Hello {user_name or 'User'},

Thank you for registering with PLPG Learning Platform!

Please verify your email address by clicking the link below:
{verification_link}

This link will expire in {s['token_expiry_hours']} hours.

If you didn't create an account, you can safely ignore this email.

Best regards,
PLPG Learning Platform Team
        """
        
        return EmailService.send_email(
            to,
            'Verify Your Email Address - PLPG Learning Platform',
            html_content,
            text_content
        )
    
    @staticmethod
    def send_password_reset_email(to: str, token: str, user_name: str = None) -> bool:
        """
        Send password reset email
        
        Args:
            to: Recipient email address
            token: Password reset token
            user_name: User's name
            
        Returns:
            True if sent successfully
        """
        s = _email_settings()
        reset_link = f"{s['frontend_base_url']}/reset-password?token={token}"
        
        html_content = EmailService._get_password_reset_email_html(
            user_name or 'User',
            reset_link
        )
        
        text_content = f"""
Hello {user_name or 'User'},

We received a request to reset your password for your PLPG Learning Platform account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email.

Best regards,
PLPG Learning Platform Team
        """
        
        return EmailService.send_email(
            to,
            'Reset Your Password - PLPG Learning Platform',
            html_content,
            text_content
        )
    
    @staticmethod
    def send_welcome_email(to: str, user_name: str = None) -> bool:
        """
        Send welcome email after email verification
        
        Args:
            to: Recipient email address
            user_name: User's name
            
        Returns:
            True if sent successfully
        """
        s = _email_settings()
        html_content = EmailService._get_welcome_email_html(
            user_name or 'User',
            s['frontend_base_url'],
        )

        text_content = f"""
Welcome to PLPG Learning Platform, {user_name or 'User'}!

Your email has been verified successfully. You're all set to start your learning journey!

Get started:
- Complete your profile
- Take the interest assessment
- Explore personalized learning paths

Visit: {s['frontend_base_url']}

Best regards,
PLPG Learning Platform Team
        """
        
        return EmailService.send_email(
            to,
            'Welcome to PLPG Learning Platform!',
            html_content,
            text_content
        )
    
    @staticmethod
    def _get_verification_email_html(user_name: str, verification_link: str, token_hours: int) -> str:
        """Generate verification email HTML template"""
        current_year = datetime.now().year
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email Address</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; background-color: #f0f2f5; margin: 0; padding: 0;">
    <div style="width: 100%; background-color: #f0f2f5; padding: 40px 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 48px 40px; text-align: center;">
                <div style="margin-bottom: 24px;">
                    <div style="width: 80px; height: 80px; background-color: rgba(255, 255, 255, 0.2); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
                        <span style="color: #ffffff; font-size: 14px; font-weight: 700; letter-spacing: 0.05em;">PLPG</span>
                    </div>
                </div>
                <h1 style="color: #ffffff; font-size: 28px; font-weight: 600; margin: 0;">Verify Your Email</h1>
            </div>
            
            <!-- Body -->
            <div style="padding: 48px 40px;">
                <p style="font-size: 20px; font-weight: 600; color: #1c1e21; margin-bottom: 24px;">Hello {user_name}!</p>
                
                <p style="color: #65676b; font-size: 16px; line-height: 1.5; margin-bottom: 32px;">
                    Thank you for registering with PLPG Learning Platform! Please verify your email address by clicking the button below.
                </p>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{verification_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #65676b; font-size: 14px; margin-top: 32px;">
                    This link will expire in {token_hours} hours. If you didn't create an account, you can safely ignore this email.
                </p>
                <p style="color: #90949c; font-size: 13px; margin-top: 24px; word-break: break-all;">
                    If the button does not work, copy this address into your browser:<br/>
                    <span style="color: #65676b;">{verification_link}</span>
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 24px 40px; text-align: center; border-top: 1px solid #e4e6eb;">
                <p style="color: #65676b; font-size: 12px; margin: 0;">
                    &copy; {current_year} PLPG Learning Platform. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
        """
    
    @staticmethod
    def _get_password_reset_email_html(user_name: str, reset_link: str) -> str:
        """Generate password reset email HTML template"""
        current_year = datetime.now().year
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; background-color: #f0f2f5; margin: 0; padding: 0;">
    <div style="width: 100%; background-color: #f0f2f5; padding: 40px 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 48px 40px; text-align: center;">
                <div style="margin-bottom: 24px;">
                    <div style="width: 80px; height: 80px; background-color: rgba(255, 255, 255, 0.2); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
                        <span style="color: #ffffff; font-size: 32px; font-weight: 700;">🔐</span>
                    </div>
                </div>
                <h1 style="color: #ffffff; font-size: 28px; font-weight: 600; margin: 0;">Reset Your Password</h1>
            </div>
            
            <!-- Body -->
            <div style="padding: 48px 40px;">
                <p style="font-size: 20px; font-weight: 600; color: #1c1e21; margin-bottom: 24px;">Hello {user_name}!</p>
                
                <p style="color: #65676b; font-size: 16px; line-height: 1.5; margin-bottom: 32px;">
                    We received a request to reset your password. Click the button below to create a new password.
                </p>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{reset_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                        Reset Password
                    </a>
                </div>
                
                <p style="color: #65676b; font-size: 14px; margin-top: 32px;">
                    This link will expire in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 24px 40px; text-align: center; border-top: 1px solid #e4e6eb;">
                <p style="color: #65676b; font-size: 12px; margin: 0;">
                    &copy; {current_year} PLPG Learning Platform. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
        """
    
    @staticmethod
    def _get_welcome_email_html(user_name: str, frontend_base_url: str) -> str:
        """Generate welcome email HTML template"""
        current_year = datetime.now().year
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to PLPG Learning Platform</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1c1e21; background-color: #f0f2f5; margin: 0; padding: 0;">
    <div style="width: 100%; background-color: #f0f2f5; padding: 40px 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); overflow: hidden;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 48px 40px; text-align: center;">
                <div style="margin-bottom: 24px;">
                    <div style="width: 80px; height: 80px; background-color: rgba(255, 255, 255, 0.2); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
                        <span style="color: #ffffff; font-size: 32px; font-weight: 700;">🎉</span>
                    </div>
                </div>
                <h1 style="color: #ffffff; font-size: 28px; font-weight: 600; margin: 0;">Welcome!</h1>
            </div>
            
            <!-- Body -->
            <div style="padding: 48px 40px;">
                <p style="font-size: 20px; font-weight: 600; color: #1c1e21; margin-bottom: 24px;">Hello {user_name}!</p>
                
                <p style="color: #65676b; font-size: 16px; line-height: 1.5; margin-bottom: 32px;">
                    Your email has been verified successfully! You're all set to start your personalized learning journey with PLPG Learning Platform.
                </p>
                
                <h3 style="color: #1c1e21; margin-bottom: 16px;">Get Started:</h3>
                <ul style="color: #65676b; font-size: 16px; padding-left: 20px;">
                    <li style="margin-bottom: 8px;">Complete your learning profile</li>
                    <li style="margin-bottom: 8px;">Take the interest assessment</li>
                    <li style="margin-bottom: 8px;">Explore personalized learning paths</li>
                </ul>
                
                <div style="text-align: center; margin: 32px 0;">
                    <a href="{frontend_base_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 8px; font-weight: 600; font-size: 16px;">
                        Start Learning
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f8f9fa; padding: 24px 40px; text-align: center; border-top: 1px solid #e4e6eb;">
                <p style="color: #65676b; font-size: 12px; margin: 0;">
                    &copy; {current_year} PLPG Learning Platform. All rights reserved.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
        """


# Convenience functions
def send_verification_email(to: str, token: str, user_name: str = None) -> bool:
    return EmailService.send_verification_email(to, token, user_name)


def send_password_reset_email(to: str, token: str, user_name: str = None) -> bool:
    return EmailService.send_password_reset_email(to, token, user_name)


def send_welcome_email(to: str, user_name: str = None) -> bool:
    return EmailService.send_welcome_email(to, user_name)
