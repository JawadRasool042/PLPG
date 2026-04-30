"""Services package"""

from services.email_service import (
    EmailService,
    send_verification_email,
    send_password_reset_email,
    send_welcome_email
)

__all__ = [
    'EmailService',
    'send_verification_email',
    'send_password_reset_email',
    'send_welcome_email'
]
