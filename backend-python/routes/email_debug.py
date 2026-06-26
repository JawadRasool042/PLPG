"""Email diagnostics - dev-only endpoints to inspect SMTP/email configuration."""

from flask import Blueprint, jsonify, request
from config import get_config
from services.email_service import get_email_config_status, EmailService
from dotenv import dotenv_values
from pathlib import Path


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


def _mask(v: str) -> str:
    if v is None:
        return ''
    s = str(v)
    if not s:
        return ''
    # show only first and last char for secrets
    if len(s) <= 4:
        return '****'
    return s[0] + '***' + s[-1]


def _looks_like_placeholder(key: str, value) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    if not s:
        return True
    lowered = s.lower()
    if key in {'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_PASS', 'EMAIL_FROM', 'SMTP_HOST', 'SMTP_EHLO_HOSTNAME', 'EMAIL_HOST'}:
        if any(hint in lowered for hint in _PLACEHOLDER_HINTS):
            return True
        if 'your' in lowered and ('password' in lowered or 'email' in lowered):
            return True
    return False

bp = Blueprint('email_debug', __name__)


@bp.route('/email-config-status', methods=['GET'])
def email_config_status():
    """Return email configuration readiness and last SMTP error (dev only)."""
    config = get_config()
    if getattr(config, 'IS_PRODUCTION', False):
        return jsonify({'error': 'Not available in production'}), 403

    status = get_email_config_status()
    last_err = EmailService.get_last_error()
    payload = {
        'status': status,
        'smtp_last_error': last_err,
    }
    return jsonify(payload)


@bp.route('/email-config-files', methods=['GET'])
def email_config_files():
    """Read repo-root .env and backend .env files and report masked values (dev only).

    Useful when you changed .env on disk but haven't restarted the server yet.
    """
    config = get_config()
    if getattr(config, 'IS_PRODUCTION', False):
        return jsonify({'error': 'Not available in production'}), 403

    backend_file = Path(__file__).resolve().parent.parent / '.env'
    repo_file = Path(__file__).resolve().parent.parent.parent / '.env'

    bb = dotenv_values(backend_file) if backend_file.exists() else {}
    rb = dotenv_values(repo_file) if repo_file.exists() else {}

    def pick(key):
        v = bb.get(key)
        if _looks_like_placeholder(key, v):
            v = rb.get(key)
        if _looks_like_placeholder(key, v):
            return None
        return v

    keys = [
        'EMAIL_SERVICE', 'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_PASS', 'EMAIL_FROM',
        'SMTP_HOST', 'SMTP_PORT', 'EMAIL_USE_TLS', 'ALLOW_DEV_EMAIL_WITHOUT_SMTP'
    ]

    data = {k: _mask(pick(k)) for k in keys}
    # Indicate which file supplied the value
    sources = {}
    for k in keys:
        if not _looks_like_placeholder(k, bb.get(k)):
            sources[k] = 'backend-python/.env'
        elif not _looks_like_placeholder(k, rb.get(k)):
            sources[k] = 'repo-root .env'
        else:
            sources[k] = None

    return jsonify({'masked': data, 'source': sources, 'backend_env_path': str(backend_file), 'repo_env_path': str(repo_file)})


@bp.route('/send-test-email', methods=['POST'])
def send_test_email():
    """Send a simple test email to validate SMTP credentials (dev only)."""
    config = get_config()
    if getattr(config, 'IS_PRODUCTION', False):
        return jsonify({'error': 'Not available in production'}), 403

    payload = request.get_json(silent=True) or {}
    to_addr = (payload.get('to') or '').strip()
    if not to_addr:
        return jsonify({'error': 'Missing "to" address'}), 400

    subject = payload.get('subject') or 'PLPG Test Email'
    html = (
        '<p>This is a test email from PLPG.</p>'
        '<p>If you received this, SMTP is configured correctly.</p>'
    )
    text = 'This is a test email from PLPG. If you received this, SMTP works.'

    ok = EmailService.send_email(to_addr, subject, html, text)
    return jsonify({
        'sent': bool(ok),
        'smtp_last_error': EmailService.get_last_error(),
    })
