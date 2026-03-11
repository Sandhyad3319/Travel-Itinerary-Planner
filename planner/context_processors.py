from django.conf import settings

def site_info(request):
    """Add site information to all templates"""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'AI Travel Planner'),
        'SITE_DOMAIN': getattr(settings, 'SITE_DOMAIN', 'http://127.0.0.1:8000'),
        'SITE_DESCRIPTION': getattr(settings, 'SITE_DESCRIPTION', 'AI-Powered Travel Itinerary Planner'),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', 'support@travelplanner.com'),
        'DEBUG': settings.DEBUG,
    }