from django.urls import path
from . import views

urlpatterns = [
    # Core Pages
    path('', views.home, name='home'),
    
    # Authentication URLs
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    
    # Itinerary Management URLs
    path('create-itinerary/', views.create_itinerary, name='create_itinerary'),
    path('itineraries/', views.itinerary_list, name='itinerary_list'),
    path('itinerary/<int:pk>/', views.itinerary_detail, name='itinerary_detail'),
    path('itinerary/<int:pk>/regenerate/', views.regenerate_itinerary, name='regenerate_itinerary'),
    path('itinerary/<int:pk>/delete/', views.delete_itinerary, name='delete_itinerary'),
    path('itinerary/<int:pk>/duplicate/', views.duplicate_itinerary, name='duplicate_itinerary'),
    
    # Additional Features
    path('stats/', views.itinerary_stats, name='itinerary_stats'),
    path('search/', views.search_itineraries, name='search_itineraries'),
    
    # Voice Assistant URLs
    path('voice-assistant/', views.voice_assistant, name='voice_assistant'),
    path('api/voice/process/', views.api_voice_process, name='api_voice_process'),
    path('api/voice/start/', views.api_voice_start, name='api_voice_start'),
    path('api/voice/status/', views.api_voice_status, name='api_voice_status'),
    path('voice-create/', views.voice_create_itinerary, name='voice_create_itinerary'),
    
    # API Endpoints
    path('api/itineraries/', views.api_itinerary_list, name='api_itinerary_list'),
    path('api/itinerary/<int:pk>/', views.api_itinerary_detail, name='api_itinerary_detail'),
path('api/voice/conversation/', views.api_voice_conversation, name='api_voice_conversation'),
]