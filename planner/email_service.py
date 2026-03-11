from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import time
from threading import Thread

logger = logging.getLogger(__name__)

def send_otp_email(email, otp_code):
    """Send OTP verification email with enhanced features"""
    try:
        logger.info(f"🔄 Attempting to send OTP email to: {email}")
        
        subject = '🔐 Your OTP Code - AI Travel Planner'
        
        context = {
            'otp_code': otp_code,
            'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
            'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
            'current_year': time.strftime("%Y"),
            'expiry_minutes': 10
        }
        
        html_content = render_to_string('planner/emails/otp_verification.html', context)
        text_content = strip_tags(html_content)
        
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            headers={
                'X-Priority': '1',
                'X-Mailer': 'AI Travel Planner',
                'Important': 'Yes',
            }
        )
        email_msg.attach_alternative(html_content, "text/html")
        
        start_time = time.time()
        sent_count = email_msg.send(fail_silently=False)
        send_time = time.time() - start_time
        
        if sent_count > 0:
            logger.info(f"✅ OTP email successfully sent to {email} in {send_time:.2f}s")
            return True
        else:
            logger.error(f"❌ Failed to send OTP email to {email} - sent_count: {sent_count}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error sending OTP email to {email}: {str(e)}", exc_info=True)
        return False

def send_welcome_email(user):
    """Send welcome email to new user with enhanced features"""
    try:
        logger.info(f"🔄 Attempting to send welcome email to: {user.email}")
        
        subject = '🎉 Welcome to AI Travel Planner! Start Your Journey'
        
        context = {
            'user': user,
            'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
            'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
            'current_year': time.strftime("%Y"),
            'login_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000')}/planner/login/"
        }
        
        html_content = render_to_string('planner/emails/welcome_email.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            headers={
                'X-Priority': '1',
                'X-Mailer': 'AI Travel Planner',
                'List-Unsubscribe': f'<{getattr(settings, "SITE_DOMAIN", "http://127.0.0.1:8000")}/unsubscribe/>',
            }
        )
        email.attach_alternative(html_content, "text/html")
        
        start_time = time.time()
        sent_count = email.send(fail_silently=False)
        send_time = time.time() - start_time
        
        if sent_count > 0:
            logger.info(f"✅ Welcome email successfully sent to {user.email} in {send_time:.2f}s")
            return True
        else:
            logger.error(f"❌ Failed to send welcome email to {user.email} - sent_count: {sent_count}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error sending welcome email to {user.email}: {str(e)}", exc_info=True)
        return False

def send_itinerary_created_email(user, itinerary):
    """Send email when itinerary is created with enhanced features"""
    try:
        logger.info(f"🔄 Attempting to send itinerary email to: {user.email} for itinerary: {itinerary.title}")
        
        subject = f'✈️ Your {itinerary.destination} Itinerary is Ready!'
        
        # Calculate duration and other details
        duration = itinerary.duration()
        total_travelers = itinerary.total_travelers()
        
        context = {
            'user': user,
            'itinerary': itinerary,
            'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
            'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
            'duration': duration,
            'total_travelers': total_travelers,
            'itinerary_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000')}/planner/itinerary/{itinerary.id}/",
            'current_year': time.strftime("%Y")
        }
        
        html_content = render_to_string('planner/emails/itinerary_created.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            headers={
                'X-Priority': '1',
                'X-Mailer': 'AI Travel Planner',
                'List-Unsubscribe': f'<{getattr(settings, "SITE_DOMAIN", "http://127.0.0.1:8000")}/unsubscribe/>',
            }
        )
        email.attach_alternative(html_content, "text/html")
        
        start_time = time.time()
        sent_count = email.send(fail_silently=False)
        send_time = time.time() - start_time
        
        if sent_count > 0:
            logger.info(f"✅ Itinerary email successfully sent to {user.email} in {send_time:.2f}s")
            return True
        else:
            logger.error(f"❌ Failed to send itinerary email to {user.email}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error sending itinerary email to {user.email}: {str(e)}", exc_info=True)
        return False

def send_password_reset_email(user, reset_url):
    """Send enhanced password reset email"""
    try:
        logger.info(f"🔄 Attempting to send password reset email to: {user.email}")
        
        subject = '🔐 Password Reset Request - AI Travel Planner'
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
            'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
            'expiry_hours': 24,
            'current_year': time.strftime("%Y")
        }
        
        html_content = render_to_string('planner/emails/password_reset_custom.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            headers={
                'X-Priority': '1',
                'X-Mailer': 'AI Travel Planner',
                'Important': 'Yes',
            }
        )
        email.attach_alternative(html_content, "text/html")
        
        sent_count = email.send(fail_silently=False)
        
        if sent_count > 0:
            logger.info(f"✅ Password reset email successfully sent to {user.email}")
            return True
        else:
            logger.error(f"❌ Failed to send password reset email to {user.email}")
            return False
            
    except Exception as e:
        logger.error(f"💥 Error sending password reset email to {user.email}: {str(e)}")
        return False

def send_bulk_email(users, subject, template_name, context_generator):
    """Send bulk emails to multiple users (for newsletters, etc.)"""
    try:
        logger.info(f"🔄 Starting bulk email send to {len(users)} users")
        
        successful_sends = 0
        failed_sends = 0
        
        for user in users:
            try:
                # Generate user-specific context
                context = context_generator(user)
                context.update({
                    'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
                    'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
                    'current_year': time.strftime("%Y")
                })
                
                html_content = render_to_string(f'planner/emails/{template_name}', context)
                text_content = strip_tags(html_content)
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                    reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)]
                )
                email.attach_alternative(html_content, "text/html")
                
                if email.send(fail_silently=True) > 0:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    logger.warning(f"⚠️ Failed to send bulk email to {user.email}")
                    
            except Exception as e:
                failed_sends += 1
                logger.error(f"💥 Error in bulk email for {user.email}: {str(e)}")
        
        logger.info(f"📧 Bulk email completed: {successful_sends} successful, {failed_sends} failed")
        return successful_sends, failed_sends
        
    except Exception as e:
        logger.error(f"💥 Error in bulk email process: {str(e)}")
        return 0, len(users)

def test_email_configuration():
    """Test function to verify email configuration is working"""
    try:
        from django.contrib.auth.models import User
        
        # Create a test user
        test_user = User(
            email='test@example.com',
            first_name='Test',
            username='testuser'
        )
        
        logger.info("🧪 Testing email configuration...")
        
        # Test welcome email
        welcome_success = send_welcome_email(test_user)
        
        # Test basic email sending
        test_email = EmailMultiAlternatives(
            subject='🧪 Test Email - AI Travel Planner',
            body='This is a test email to verify your email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else ['test@example.com']
        )
        
        test_sent = test_email.send(fail_silently=True) > 0
        
        if welcome_success or test_sent:
            logger.info("✅ Email configuration test passed!")
            return True
        else:
            logger.warning("⚠️ Email configuration test had issues - check your settings")
            return False
            
    except Exception as e:
        logger.error(f"💥 Email configuration test failed: {str(e)}")
        return False

def send_email_async(email_function, *args, **kwargs):
    """Send email in background thread to avoid blocking the main request"""
    def send_in_thread():
        try:
            email_function(*args, **kwargs)
        except Exception as e:
            logger.error(f"💥 Error in async email sending: {str(e)}")
    
    email_thread = Thread(target=send_in_thread)
    email_thread.daemon = True
    email_thread.start()
    return email_thread

# Utility function to check email settings
def get_email_status():
    """Return current email configuration status"""
    status = {
        'email_backend': settings.EMAIL_BACKEND,
        'email_host': settings.EMAIL_HOST,
        'email_port': settings.EMAIL_PORT,
        'email_use_tls': settings.EMAIL_USE_TLS,
        'default_from_email': settings.DEFAULT_FROM_EMAIL,
        'email_host_user_set': bool(settings.EMAIL_HOST_USER),
        'debug_mode': settings.DEBUG,
    }
    
    logger.info(f"📧 Email Status: {status}")
    return status

def send_registration_otp_async(email, otp_code):
    """Send OTP email asynchronously for better performance"""
    return send_email_async(send_otp_email, email, otp_code)

def send_welcome_email_async(user):
    """Send welcome email asynchronously"""
    return send_email_async(send_welcome_email, user)

def send_itinerary_email_async(user, itinerary):
    """Send itinerary email asynchronously"""
    return send_email_async(send_itinerary_created_email, user, itinerary)

def send_welcome_email(user):
    """Send welcome email to new user with enhanced error handling"""
    try:
        print(f"🔄 Attempting to send welcome email to: {user.email}")
        
        subject = '🎉 Welcome to AI Travel Planner! Start Your Journey'
        
        # Create context with site information
        context = {
            'user': user,
            'site_name': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
            'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
        }
        
        # Create HTML content
        html_content = render_to_string('planner/emails/welcome_email.html', context)
        
        # Create plain text content
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[getattr(settings, 'REPLY_TO_EMAIL', settings.DEFAULT_FROM_EMAIL)]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        sent_count = email.send(fail_silently=False)
        
        if sent_count > 0:
            print(f"✅ Welcome email successfully sent to {user.email}")
            return True
        else:
            print(f"❌ Failed to send welcome email to {user.email}")
            return False
            
    except Exception as e:
        print(f"💥 Error sending welcome email to {user.email}: {str(e)}")
        return False