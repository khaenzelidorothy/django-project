from datetime import datetime
import random
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    return str(random.randint(100000, 999999))

def send_forgot_password_email(email, otp):
    if not email:
        raise ValueError("Email address is required for sending OTP email.")
    subject = 'Reset Your Password - CraftCrest App'
    message = f'Your password reset code is: {otp}. Use this to reset your password.'
    html_message = render_to_string('emails/forgot_password.html', {'otp': otp})
    logger.debug(f"Sending forgot password email to {email} with OTP {otp}")
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )
    logger.debug(f"Forgot password email with OTP {otp} sent to {email}")

def send_verification_email(email, otp):
    subject = 'Verify Your Email - CraftCrest App'
    message = f'Your verification code is: {otp}'
    html_message = render_to_string('emails/verification.html', {'otp': otp})
    if not email:
        raise ValueError("Email address is required for sending verification email.")
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )
    logger.debug(f"Verification email with OTP {otp} sent to {email}")