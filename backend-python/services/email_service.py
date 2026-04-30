"""
============================================
Email Service Module
============================================

Handles all email sending functionality using SMTP
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import get_config

config = get_config()


class EmailService:
    """Email service class for sending emails"""
    
    _transporter = None
    
    @staticmethod
    def _get_transporter():
        """Get or create SMTP transporter"""
        if not config.EMAIL_USER or not config.EMAIL_PASSWORD:
            print('❌ Email service not configured (missing EMAIL_USER or EMAIL_PASSWORD)')
            return None
        
        return {
            'host': 'smtp.gmail.com',
            'port': 587,
            'user': config.EMAIL_USER,
            'password': config.EMAIL_PASSWORD
        }
    
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
        import logging
        logger = logging.getLogger(__name__)
        
        transporter = EmailService._get_transporter()
        if not transporter:
            logger.warning('Email service not configured')
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config.EMAIL_FROM or config.EMAIL_USER
            msg['To'] = to
            
            # Attach plain text and HTML versions
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Connect and send with timeout
            with smtplib.SMTP(transporter['host'], transporter['port'], timeout=10) as server:
                server.starttls()
                server.login(transporter['user'], transporter['password'])
                server.sendmail(transporter['user'], to, msg.as_string())
            
            logger.info(f'✓ Email sent to {to}')
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f'SMTP Authentication failed: {e}')
            return False
        except smtplib.SMTPException as e:
            logger.error(f'SMTP error sending to {to}: {e}')
            return False
        except Exception as e:
            logger.error(f'Unexpected error sending email to {to}: {e}')
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
        verification_link = f"{config.FRONTEND_BASE_URL}/verify-email?token={token}"
        
        html_content = EmailService._get_verification_email_html(
            user_name or 'User',
            verification_link
        )
        
        text_content = f"""
Hello {user_name or 'User'},

Thank you for registering with PLPG Learning Platform!

Please verify your email address by clicking the link below:
{verification_link}

This link will expire in {config.EMAIL_TOKEN_EXPIRY_HOURS} hours.

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
        reset_link = f"{config.FRONTEND_BASE_URL}/reset-password?token={token}"
        
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
        html_content = EmailService._get_welcome_email_html(user_name or 'User')
        
        text_content = f"""
Welcome to PLPG Learning Platform, {user_name or 'User'}!

Your email has been verified successfully. You're all set to start your learning journey!

Get started:
- Complete your profile
- Take the interest assessment
- Explore personalized learning paths

Visit: {config.FRONTEND_BASE_URL}

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
    def _get_verification_email_html(user_name: str, verification_link: str) -> str:
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
                        <span style="color: #ffffff; font-size: 32px; font-weight: 700;">📚</span>
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
                    This link will expire in {config.EMAIL_TOKEN_EXPIRY_HOURS} hours. If you didn't create an account, you can safely ignore this email.
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
    def _get_welcome_email_html(user_name: str) -> str:
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
                    <a href="{config.FRONTEND_BASE_URL}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 8px; font-weight: 600; font-size: 16px;">
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
