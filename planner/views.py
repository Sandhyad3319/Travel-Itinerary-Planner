from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
from threading import Thread
import speech_recognition as sr
import pyttsx3
import threading
import time
import re

from .models import Itinerary, Destination, DayPlan, Activity, OTPVerification
from .forms import ItineraryForm, CustomUserCreationForm
from .otp_forms import OTPVerificationForm
from .ai_engine import TravelAI
from .email_service import send_welcome_email, send_itinerary_created_email, send_otp_email

# Voice assistant engine (initialize once)
voice_engine = None
conversation_state = {}

def get_voice_engine():
    """Initialize text-to-speech engine"""
    global voice_engine
    if voice_engine is None:
        voice_engine = pyttsx3.init()
        voice_engine.setProperty('rate', 150)
        voice_engine.setProperty('volume', 0.8)
        # Set voice properties
        voices = voice_engine.getProperty('voices')
        if len(voices) > 1:
            voice_engine.setProperty('voice', voices[1].id)  # Female voice if available
    return voice_engine

def speak_text(text, wait=False):
    """Speak text using text-to-speech"""
    def speak():
        try:
            engine = get_voice_engine()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"🔇 Voice error: {e}")
    
    # Speak in background thread to avoid blocking
    voice_thread = threading.Thread(target=speak)
    voice_thread.daemon = True
    voice_thread.start()
    
    if wait:
        voice_thread.join()

def home(request):
    """Home page with features and information"""
    if request.user.is_authenticated:
        user_itineraries = Itinerary.objects.filter(user=request.user)
        total_itineraries = user_itineraries.count()
        recent_itineraries = user_itineraries.order_by('-created_at')[:3]
    else:
        total_itineraries = 0
        recent_itineraries = []
    
    popular_destinations = [
        {"name": "Paris, France", "trips": 42, "image": "🇫🇷", "icon": "🗼"},
        {"name": "Tokyo, Japan", "trips": 38, "image": "🇯🇵", "icon": "🏯"},
        {"name": "New York, USA", "trips": 35, "image": "🇺🇸", "icon": "🗽"},
        {"name": "Bali, Indonesia", "trips": 28, "image": "🇮🇩", "icon": "🏝️"},
    ]
    
    # Voice welcome for new visitors
    if not request.user.is_authenticated and 'voice_welcomed' not in request.session:
        request.session['voice_welcomed'] = True
        speak_text("Welcome to AI Travel Planner! I can help you create amazing travel itineraries. Click the microphone to start planning with your voice!")
    
    context = {
        'total_itineraries': total_itineraries,
        'recent_itineraries': recent_itineraries,
        'popular_destinations': popular_destinations,
    }
    
    return render(request, 'planner/home.html', context)

def register(request):
    """Step 1: User registration with OTP sending"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Save user data in session instead of creating user
            user_data = {
                'username': form.cleaned_data['username'],
                'email': form.cleaned_data['email'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'password': form.cleaned_data['password1'],
            }
            
            # Generate and send OTP
            otp_obj = OTPVerification.objects.create(email=user_data['email'])
            
            # Send OTP email
            def send_otp():
                try:
                    success = send_otp_email(user_data['email'], otp_obj.otp_code)
                    if success:
                        print(f"✅ OTP sent to {user_data['email']}")
                    else:
                        print(f"❌ Failed to send OTP to {user_data['email']}")
                except Exception as e:
                    print(f"💥 OTP email error: {e}")
            
            # Send OTP in background
            otp_thread = Thread(target=send_otp)
            otp_thread.daemon = True
            otp_thread.start()
            
            # Store data in session for verification step
            request.session['pending_registration'] = user_data
            request.session['otp_id'] = otp_obj.id
            
            messages.info(request, f'📧 OTP sent to {user_data["email"]}. Please check your email and enter the code below.')
            return redirect('verify_otp')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'planner/register.html', {'form': form})

def verify_otp(request):
    """Step 2: OTP verification and user creation"""
    # Check if user came from registration
    if 'pending_registration' not in request.session:
        messages.error(request, '❌ Please complete registration first.')
        return redirect('register')
    
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            otp_id = request.session.get('otp_id')
            
            try:
                otp_obj = OTPVerification.objects.get(id=otp_id, email=request.session['pending_registration']['email'])
                
                if otp_obj.is_expired():
                    messages.error(request, '❌ OTP has expired. Please register again.')
                    # Clear session and redirect to registration
                    del request.session['pending_registration']
                    del request.session['otp_id']
                    return redirect('register')
                
                if otp_obj.otp_code == otp_code:
                    # OTP verified - create user account
                    user_data = request.session['pending_registration']
                    
                    from django.contrib.auth.models import User
                    user = User.objects.create_user(
                        username=user_data['username'],
                        email=user_data['email'],
                        password=user_data['password'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name']
                    )
                    
                    # Mark OTP as verified
                    otp_obj.is_verified = True
                    otp_obj.save()
                    
                    # Clear session data
                    del request.session['pending_registration']
                    del request.session['otp_id']
                    
                    # Send welcome email with enhanced logging
                    def send_welcome_with_logging():
                        try:
                            print(f"🔄 Attempting to send welcome email to: {user.email}")
                            success = send_welcome_email(user)
                            if success:
                                print(f"✅ Welcome email successfully sent to: {user.email}")
                            else:
                                print(f"❌ Failed to send welcome email to: {user.email}")
                        except Exception as e:
                            print(f"💥 Error in welcome email thread: {str(e)}")
                    
                    # Send welcome email in background
                    welcome_thread = Thread(target=send_welcome_with_logging)
                    welcome_thread.daemon = True
                    welcome_thread.start()
                    
                    # Auto-login the user after registration
                    user = authenticate(username=user_data['username'], password=user_data['password'])
                    if user is not None:
                        login(request, user)
                        messages.success(request, f'🎉 Welcome {user.first_name}! Your account has been created successfully. A welcome email has been sent to {user.email}.')
                        return redirect('home')
                    else:
                        messages.success(request, '✅ Account created successfully! Please login with your credentials.')
                        return redirect('login')
                else:
                    messages.error(request, '❌ Invalid OTP code. Please try again.')
            except OTPVerification.DoesNotExist:
                messages.error(request, '❌ OTP verification failed. Please register again.')
                return redirect('register')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'planner/verify_otp.html', {
        'form': form,
        'email': request.session['pending_registration']['email']
    })

def resend_otp(request):
    """Resend OTP code"""
    if 'pending_registration' not in request.session:
        messages.error(request, '❌ Session expired. Please register again.')
        return redirect('register')
    
    user_data = request.session['pending_registration']
    
    # Create new OTP
    otp_obj = OTPVerification.objects.create(email=user_data['email'])
    request.session['otp_id'] = otp_obj.id
    
    # Send new OTP
    def resend_otp_email():
        try:
            send_otp_email(user_data['email'], otp_obj.otp_code)
        except Exception as e:
            print(f"Resend OTP error: {e}")
    
    resend_thread = Thread(target=resend_otp_email)
    resend_thread.daemon = True
    resend_thread.start()
    
    messages.info(request, '📧 New OTP sent to your email.')
    return redirect('verify_otp')

@login_required
def create_itinerary(request):
    """Create a new itinerary with AI assistance and email notification"""
    if request.method == 'POST':
        form = ItineraryForm(request.POST)
        if form.is_valid():
            try:
                itinerary = form.save(commit=False)
                itinerary.user = request.user
                itinerary.save()
                
                # Generate itinerary using AI
                ai_engine = TravelAI()
                itinerary_data = {
                    'destination': itinerary.destination,
                    'duration': itinerary.duration(),
                    'budget': itinerary.budget,
                    'trip_type': itinerary.trip_type,
                    'travelers': itinerary.travelers,
                    'special_requirements': itinerary.special_requirements,
                    'start_date': itinerary.start_date.isoformat()
                }
                
                # Show loading message
                messages.info(request, '🤖 AI is generating your personalized itinerary...')
                
                ai_itinerary = ai_engine.generate_itinerary(itinerary_data)
                
                # Save day plans
                days_created = 0
                activities_created = 0
                
                for day_data in ai_itinerary.get('days', []):
                    day_plan = DayPlan(
                        itinerary=itinerary,
                        day_number=day_data.get('day', 1),
                        date=itinerary.start_date + timedelta(days=day_data.get('day', 1)-1),
                        activities=day_data.get('activities', [])
                    )
                    day_plan.save()
                    days_created += 1
                    activities_created += len(day_data.get('activities', []))
                
                # Send itinerary created email in background
                def send_itinerary_email():
                    try:
                        send_itinerary_created_email(request.user, itinerary)
                        print(f"Itinerary email sent to {request.user.email}")
                    except Exception as e:
                        print(f"Failed to send itinerary email: {e}")
                
                email_thread = Thread(target=send_itinerary_email)
                email_thread.daemon = True
                email_thread.start()
                
                messages.success(
                    request, 
                    f'✅ Itinerary created successfully! Generated {days_created} days with {activities_created} activities. Check your email for details!'
                )
                return redirect('itinerary_detail', pk=itinerary.pk)
                
            except Exception as e:
                messages.error(
                    request, 
                    f'❌ Error creating itinerary: {str(e)}. Please try again.'
                )
                if 'itinerary' in locals():
                    itinerary.delete()
    else:
        form = ItineraryForm()
        
        # Pre-fill form with GET parameters for quick start
        destination_name = request.GET.get('destination', '')
        trip_type = request.GET.get('trip_type', '')
        budget = request.GET.get('budget', '')
        
        if destination_name:
            form.initial['destination'] = destination_name
        if trip_type:
            form.initial['trip_type'] = trip_type
        if budget:
            form.initial['budget'] = budget
    
    # Popular destinations for suggestions
    popular_destinations = [
        {"name": "Paris, France", "emoji": "🇫🇷", "description": "City of Love & Lights"},
        {"name": "Tokyo, Japan", "emoji": "🇯🇵", "description": "Modern & Traditional Blend"},
        {"name": "Bali, Indonesia", "emoji": "🇮🇩", "description": "Tropical Paradise"},
        {"name": "New York, USA", "emoji": "🇺🇸", "description": "The Big Apple"},
        {"name": "Rome, Italy", "emoji": "🇮🇹", "description": "Eternal City"},
        {"name": "Sydney, Australia", "emoji": "🇦🇺", "description": "Harbor City"},
    ]
    
    context = {
        'form': form,
        'popular_destinations': popular_destinations,
    }
    
    return render(request, 'planner/create_itinerary.html', context)

@login_required
def itinerary_list(request):
    """List all itineraries for the current user"""
    itineraries = Itinerary.objects.filter(user=request.user).prefetch_related('days').order_by('-created_at')
    
    # Calculate statistics
    total_itineraries = itineraries.count()
    total_days = sum(itinerary.duration() for itinerary in itineraries)
    total_activities = 0
    
    for itinerary in itineraries:
        for day in itinerary.days.all():
            total_activities += len(day.activities)
    
    # Group by trip type for charts
    trip_type_stats = itineraries.values('trip_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Recent activity
    recent_activity = itineraries.order_by('-updated_at')[:5]
    
    context = {
        'itineraries': itineraries,
        'total_itineraries': total_itineraries,
        'total_days': total_days,
        'total_activities': total_activities,
        'trip_type_stats': trip_type_stats,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'planner/itinerary_list.html', context)

@login_required
def itinerary_detail(request, pk):
    """View detailed itinerary"""
    itinerary = get_object_or_404(
        Itinerary.objects.prefetch_related('days'), 
        pk=pk, 
        user=request.user
    )
    days = itinerary.days.all()
    
    # Calculate total cost and statistics
    total_cost = 0
    activity_types = {}
    daily_costs = []
    
    for day in days:
        day_cost = 0
        for activity in day.activities:
            cost = activity.get('cost_estimate', 0)
            total_cost += cost
            day_cost += cost
            
            # Count activity types
            activity_type = activity.get('type', 'other')
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
        
        daily_costs.append({
            'day': day.day_number,
            'date': day.date,
            'cost': day_cost
        })
    
    # Calculate cost per traveler
    cost_per_traveler = total_cost / itinerary.travelers if itinerary.travelers > 0 else total_cost
    
    context = {
        'itinerary': itinerary,
        'days': days,
        'total_cost': total_cost,
        'cost_per_traveler': cost_per_traveler,
        'activity_types': activity_types,
        'daily_costs': daily_costs,
    }
    
    return render(request, 'planner/itinerary_detail.html', context)

@login_required
def regenerate_itinerary(request, pk):
    """Regenerate itinerary using AI"""
    if request.method == 'POST':
        itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
        
        try:
            # Delete existing day plans
            deleted_count, _ = itinerary.days.all().delete()
            
            # Regenerate with AI
            ai_engine = TravelAI()
            itinerary_data = {
                'destination': itinerary.destination,
                'duration': itinerary.duration(),
                'budget': itinerary.budget,
                'trip_type': itinerary.trip_type,
                'travelers': itinerary.travelers,
                'special_requirements': itinerary.special_requirements,
                'start_date': itinerary.start_date.isoformat()
            }
            
            messages.info(request, '🔄 Regenerating your itinerary with AI...')
            
            ai_itinerary = ai_engine.generate_itinerary(itinerary_data)
            
            # Save new day plans
            days_created = 0
            activities_created = 0
            
            for day_data in ai_itinerary.get('days', []):
                day_plan = DayPlan(
                    itinerary=itinerary,
                    day_number=day_data.get('day', 1),
                    date=itinerary.start_date + timedelta(days=day_data.get('day', 1)-1),
                    activities=day_data.get('activities', [])
                )
                day_plan.save()
                days_created += 1
                activities_created += len(day_data.get('activities', []))
            
            itinerary.updated_at = timezone.now()
            itinerary.save()
            
            messages.success(
                request, 
                f'✅ Itinerary regenerated! Created {days_created} days with {activities_created} new activities.'
            )
            
        except Exception as e:
            messages.error(
                request, 
                f'❌ Error regenerating itinerary: {str(e)}'
            )
        
        return redirect('itinerary_detail', pk=itinerary.pk)
    
    return redirect('itinerary_list')

@login_required
def delete_itinerary(request, pk):
    """Delete an itinerary"""
    if request.method == 'POST':
        itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
        itinerary_title = itinerary.title
        itinerary.delete()
        
        messages.success(request, f'🗑️ Itinerary "{itinerary_title}" has been deleted.')
        return redirect('itinerary_list')
    
    return redirect('itinerary_list')

@login_required
def duplicate_itinerary(request, pk):
    """Duplicate an existing itinerary"""
    if request.method == 'POST':
        original_itinerary = get_object_or_404(
            Itinerary.objects.prefetch_related('days'), 
            pk=pk, 
            user=request.user
        )
        
        try:
            # Create new itinerary
            new_itinerary = Itinerary(
                user=request.user,
                title=f"{original_itinerary.title} (Copy)",
                destination=original_itinerary.destination,
                start_date=original_itinerary.start_date,
                end_date=original_itinerary.end_date,
                budget=original_itinerary.budget,
                trip_type=original_itinerary.trip_type,
                travelers=original_itinerary.travelers,
                special_requirements=original_itinerary.special_requirements,
            )
            new_itinerary.save()
            
            # Duplicate day plans
            for day_plan in original_itinerary.days.all():
                new_day_plan = DayPlan(
                    itinerary=new_itinerary,
                    day_number=day_plan.day_number,
                    date=day_plan.date,
                    activities=day_plan.activities
                )
                new_day_plan.save()
            
            messages.success(request, f'📋 Itinerary duplicated successfully!')
            return redirect('itinerary_detail', pk=new_itinerary.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error duplicating itinerary: {str(e)}')
            return redirect('itinerary_list')
    
    return redirect('itinerary_list')

@login_required
def itinerary_stats(request):
    """Show user statistics"""
    user_itineraries = Itinerary.objects.filter(user=request.user)
    
    # Basic stats
    total_itineraries = user_itineraries.count()
    total_days = sum(itinerary.duration() for itinerary in user_itineraries)
    
    # Cost statistics
    total_cost = 0
    for itinerary in user_itineraries.prefetch_related('days'):
        for day in itinerary.days.all():
            for activity in day.activities:
                total_cost += activity.get('cost_estimate', 0)
    
    # Trip type distribution
    trip_type_stats = user_itineraries.values('trip_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Budget distribution
    budget_stats = user_itineraries.values('budget').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Monthly activity
    monthly_stats = user_itineraries.extra(
        {'month': "strftime('%%Y-%%m', created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    # Destination statistics
    destination_stats = user_itineraries.values('destination').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'total_itineraries': total_itineraries,
        'total_days': total_days,
        'total_cost': total_cost,
        'trip_type_stats': trip_type_stats,
        'budget_stats': budget_stats,
        'monthly_stats': monthly_stats,
        'destination_stats': destination_stats,
    }
    
    return render(request, 'planner/itinerary_stats.html', context)

# API Views for AJAX calls
@login_required
def api_itinerary_list(request):
    """API endpoint for itinerary list (for potential mobile app)"""
    itineraries = Itinerary.objects.filter(user=request.user).values(
        'id', 'title', 'destination', 'start_date', 'end_date', 
        'budget', 'trip_type', 'created_at'
    ).order_by('-created_at')
    
    return JsonResponse(list(itineraries), safe=False)

@login_required
def api_itinerary_detail(request, pk):
    """API endpoint for itinerary detail"""
    itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
    
    data = {
        'id': itinerary.id,
        'title': itinerary.title,
        'destination': itinerary.destination,
        'start_date': itinerary.start_date.isoformat(),
        'end_date': itinerary.end_date.isoformat(),
        'budget': itinerary.budget,
        'trip_type': itinerary.trip_type,
        'travelers': itinerary.travelers,
        'special_requirements': itinerary.special_requirements,
        'days': []
    }
    
    for day in itinerary.days.all():
        day_data = {
            'day_number': day.day_number,
            'date': day.date.isoformat(),
            'activities': day.activities
        }
        data['days'].append(day_data)
    
    return JsonResponse(data)

@login_required
def search_itineraries(request):
    """Search itineraries by destination, title, or trip type"""
    query = request.GET.get('q', '')
    
    if query:
        itineraries = Itinerary.objects.filter(
            user=request.user
        ).filter(
            Q(title__icontains=query) |
            Q(destination__icontains=query) |
            Q(trip_type__icontains=query) |
            Q(special_requirements__icontains=query)
        ).order_by('-created_at')
    else:
        itineraries = Itinerary.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'itineraries': itineraries,
        'query': query,
        'results_count': itineraries.count()
    }
    
    return render(request, 'planner/itinerary_list.html', context)

# ============================================================================
# INTERACTIVE VOICE ASSISTANT - CONVERSATIONAL PLANNING
# ============================================================================

def voice_assistant(request):
    """Interactive voice assistant page"""
    # Initialize conversation state for this session
    if 'conversation_id' not in request.session:
        request.session['conversation_id'] = str(time.time())
        request.session['conversation_step'] = 'welcome'
        request.session['itinerary_data'] = {}
    
    return render(request, 'planner/voice_assistant.html')

@login_required
def api_voice_process(request):
    """Process voice commands with conversation flow"""
    if request.method == 'POST' and request.FILES.get('audio'):
        try:
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Get audio file
            audio_file = request.FILES['audio']
            
            # Convert to audio data
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
                
            # Recognize speech
            user_speech = recognizer.recognize_google(audio_data)
            
            # Process based on conversation step
            conversation_step = request.session.get('conversation_step', 'welcome')
            itinerary_data = request.session.get('itinerary_data', {})
            
            response = handle_conversation_step(conversation_step, user_speech, itinerary_data, request.user)
            
            # Update session state
            request.session['conversation_step'] = response.get('next_step', conversation_step)
            request.session['itinerary_data'] = response.get('updated_data', itinerary_data)
            
            # Speak the response
            speak_text(response['message'])
            
            return JsonResponse({
                'success': True,
                'text': user_speech,
                'response': response
            })
            
        except sr.UnknownValueError:
            error_msg = "I didn't catch that. Could you please repeat?"
            speak_text(error_msg)
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        except sr.RequestError as e:
            error_msg = "There's an issue with speech recognition. Please try again."
            speak_text(error_msg)
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
        except Exception as e:
            error_msg = "Something went wrong. Let's start over."
            speak_text(error_msg)
            return JsonResponse({
                'success': False,
                'error': error_msg
            })
    
    return JsonResponse({'success': False, 'error': 'No audio file'})

def handle_conversation_step(step, user_input, itinerary_data, user):
    """Handle different steps in the conversation flow"""
    user_input_lower = user_input.lower()
    
    if step == 'welcome':
        return handle_welcome_step(user_input_lower, itinerary_data)
    
    elif step == 'destination':
        return handle_destination_step(user_input_lower, itinerary_data)
    
    elif step == 'duration':
        return handle_duration_step(user_input_lower, itinerary_data)
    
    elif step == 'travelers':
        return handle_travelers_step(user_input_lower, itinerary_data)
    
    elif step == 'budget':
        return handle_budget_step(user_input_lower, itinerary_data)
    
    elif step == 'trip_type':
        return handle_trip_type_step(user_input_lower, itinerary_data)
    
    elif step == 'special_requirements':
        return handle_special_requirements_step(user_input_lower, itinerary_data)
    
    elif step == 'confirm':
        return handle_confirm_step(user_input_lower, itinerary_data, user)
    
    elif step == 'complete':
        return handle_complete_step(user_input_lower, itinerary_data)
    
    else:
        return {
            'message': "Let's start over. I'm your travel assistant. Would you like to create a new itinerary?",
            'next_step': 'welcome',
            'updated_data': {}
        }

def handle_welcome_step(user_input, itinerary_data):
    """Welcome step - start conversation"""
    if any(word in user_input for word in ['yes', 'yeah', 'sure', 'okay', 'create', 'new', 'plan', 'let\'s go', 'start']):
        message = "🎤 Great! Let's plan your perfect trip. First, where would you like to go? Tell me your dream destination - for example, Paris, Tokyo, or New York."
        return {
            'message': message,
            'next_step': 'destination',
            'updated_data': itinerary_data
        }
    elif any(word in user_input for word in ['no', 'not now', 'later', 'cancel']):
        message = "🎤 No problem! Whenever you're ready to plan a trip, just say 'create new itinerary' or 'I want to plan a trip'. I'll be here to help!"
        return {
            'message': message,
            'next_step': 'welcome',
            'updated_data': {}
        }
    else:
        message = "🎤 I'm your travel assistant. I can help you create amazing travel itineraries. Would you like to plan a new trip? Say yes to continue or no to cancel."
        return {
            'message': message,
            'next_step': 'welcome',
            'updated_data': {}
        }

def handle_destination_step(user_input, itinerary_data):
    """Handle destination input"""
    if user_input.strip():
        # Extract destination from user input
        destination = extract_destination(user_input)
        itinerary_data['destination'] = destination
        
        message = f"🎤 Wonderful! {destination} sounds amazing. How many days would you like to spend there? For example, you could say 5 days, one week, or 10 days."
        return {
            'message': message,
            'next_step': 'duration',
            'updated_data': itinerary_data
        }
    else:
        message = "🎤 I didn't catch the destination. Where would you like to go? For example, you could say Paris, Tokyo, or New York."
        return {
            'message': message,
            'next_step': 'destination',
            'updated_data': itinerary_data
        }

def handle_duration_step(user_input, itinerary_data):
    """Handle duration input"""
    duration = extract_duration(user_input)
    if duration:
        itinerary_data['duration'] = duration
        
        message = f"🎤 Perfect! {duration} days in {itinerary_data['destination']}. How many people will be traveling? Just say a number like 2, or 4 people."
        return {
            'message': message,
            'next_step': 'travelers',
            'updated_data': itinerary_data
        }
    else:
        message = "🎤 How many days would you like to travel? For example, you could say 5 days, one week, or 10 days."
        return {
            'message': message,
            'next_step': 'duration',
            'updated_data': itinerary_data
        }

def handle_travelers_step(user_input, itinerary_data):
    """Handle number of travelers"""
    travelers = extract_travelers(user_input)
    if travelers:
        itinerary_data['travelers'] = travelers
        
        message = f"🎤 Got it! {travelers} travelers. What's your budget preference? You can say budget friendly, moderate spending, or luxury experience."
        return {
            'message': message,
            'next_step': 'budget',
            'updated_data': itinerary_data
        }
    else:
        message = "🎤 How many people will be traveling? Just say a number like 2, 4, or 6 people."
        return {
            'message': message,
            'next_step': 'travelers',
            'updated_data': itinerary_data
        }

def handle_budget_step(user_input, itinerary_data):
    """Handle budget preference"""
    budget = extract_budget(user_input)
    if budget:
        itinerary_data['budget'] = budget
        
        message = f"🎤 {budget.capitalize()} budget, excellent! What type of trip are you looking for? You can say adventure, relaxation, cultural, romantic, or family trip."
        return {
            'message': message,
            'next_step': 'trip_type',
            'updated_data': itinerary_data
        }
    else:
        message = "🎤 What's your budget preference? You can say budget friendly, moderate spending, or luxury experience."
        return {
            'message': message,
            'next_step': 'budget',
            'updated_data': itinerary_data
        }

def handle_trip_type_step(user_input, itinerary_data):
    """Handle trip type"""
    trip_type = extract_trip_type(user_input)
    if trip_type:
        itinerary_data['trip_type'] = trip_type
        
        message = f"🎤 A {trip_type} trip, perfect! Do you have any special requirements or preferences? For example, dietary restrictions, accessibility needs, or specific interests like museums or beaches. If not, just say 'no'."
        return {
            'message': message,
            'next_step': 'special_requirements',
            'updated_data': itinerary_data
        }
    else:
        message = "🎤 What type of trip would you like? Adventure, relaxation, cultural experience, romantic getaway, or family vacation?"
        return {
            'message': message,
            'next_step': 'trip_type',
            'updated_data': itinerary_data
        }

def handle_special_requirements_step(user_input, itinerary_data):
    """Handle special requirements"""
    if any(word in user_input for word in ['no', 'none', 'nothing', "don't"]):
        itinerary_data['special_requirements'] = ''
    else:
        itinerary_data['special_requirements'] = user_input
    
    # Set default dates
    start_date = datetime.now().date() + timedelta(days=7)
    end_date = start_date + timedelta(days=itinerary_data['duration'] - 1)
    itinerary_data['start_date'] = start_date.isoformat()
    itinerary_data['end_date'] = end_date.isoformat()
    
    # Create confirmation message
    requirements_text = "no special requirements" if not itinerary_data['special_requirements'] else f"special requirements: {itinerary_data['special_requirements']}"
    
    message = f"🎤 Perfect! Let me confirm your details: {itinerary_data['duration']} days in {itinerary_data['destination']} for {itinerary_data['travelers']} people, {itinerary_data['budget']} budget, {itinerary_data['trip_type']} trip, and {requirements_text}. Should I create this amazing itinerary for you? Say 'yes' to continue or 'no' to start over."
    
    return {
        'message': message,
        'next_step': 'confirm',
        'updated_data': itinerary_data
    }

def handle_confirm_step(user_input, itinerary_data, user):
    """Handle final confirmation"""
    if any(word in user_input for word in ['yes', 'yeah', 'sure', 'okay', 'create', 'please', 'go ahead']):
        # Create the itinerary
        try:
            itinerary = create_itinerary_from_voice_data(itinerary_data, user)
            message = f"🎤 Excellent! I've created your {itinerary_data['trip_type']} trip to {itinerary_data['destination']}. I'm now generating your detailed itinerary with AI. This might take a moment. You'll receive an email with all the details soon! You can view your itinerary in your dashboard."
            return {
                'message': message,
                'next_step': 'complete',
                'updated_data': {},
                'itinerary_created': True,
                'itinerary_id': itinerary.id
            }
        except Exception as e:
            message = f"🎤 I'm sorry, there was an error creating your itinerary: {str(e)}. Let's try again. Would you like to create a new itinerary?"
            return {
                'message': message,
                'next_step': 'welcome',
                'updated_data': {}
            }
    else:
        message = "🎤 No problem! Let's start over. Would you like to create a new itinerary?"
        return {
            'message': message,
            'next_step': 'welcome',
            'updated_data': {}
        }

def handle_complete_step(user_input, itinerary_data):
    """Handle completion step"""
    if any(word in user_input for word in ['new', 'another', 'create', 'plan']):
        message = "🎤 Great! Let's plan another amazing trip. Where would you like to go this time?"
        return {
            'message': message,
            'next_step': 'destination',
            'updated_data': {}
        }
    else:
        message = "🎤 Your itinerary has been created! You can view it in your dashboard. If you'd like to create another itinerary, just say 'create new itinerary'."
        return {
            'message': message,
            'next_step': 'complete',
            'updated_data': {}
        }

def extract_destination(user_input):
    """Extract destination from user input"""
    # Remove common phrases
    cleaned_input = re.sub(r'\b(?:i want to go to|i\'d like to visit|let\'s go to|travel to|visit)\b', '', user_input, flags=re.IGNORECASE).strip()
    
    # Common destinations mapping
    destination_mapping = {
        'paris': 'Paris, France',
        'tokyo': 'Tokyo, Japan',
        'london': 'London, UK',
        'new york': 'New York, USA',
        'bali': 'Bali, Indonesia',
        'rome': 'Rome, Italy',
        'sydney': 'Sydney, Australia',
        'bangkok': 'Bangkok, Thailand',
        'dubai': 'Dubai, UAE',
        'barcelona': 'Barcelona, Spain',
        'mumbai': 'Mumbai, India',
        'delhi': 'Delhi, India',
        'goa': 'Goa, India',
        'kerala': 'Kerala, India',
        'jaipur': 'Jaipur, India'
    }
    
    for key, value in destination_mapping.items():
        if key in cleaned_input.lower():
            return value
    
    # Return capitalized input as fallback
    return cleaned_input.title()

def extract_duration(user_input):
    """Extract duration from user input"""
    # Look for numbers followed by "days" or "day"
    match = re.search(r'(\d+)\s*(?:day|days)', user_input)
    if match:
        days = int(match.group(1))
        if 1 <= days <= 30:  # Reasonable range
            return days
    
    # Check for weeks
    match = re.search(r'(\d+)\s*(?:week|weeks)', user_input)
    if match:
        weeks = int(match.group(1))
        days = weeks * 7
        if 1 <= days <= 30:
            return days
    
    # Check for common duration phrases
    if 'week' in user_input or '7 days' in user_input:
        return 7
    elif 'two weeks' in user_input or '14 days' in user_input:
        return 14
    elif 'month' in user_input or '30 days' in user_input:
        return 30
    
    # Look for any number in the input
    numbers = re.findall(r'\d+', user_input)
    for num in numbers:
        days = int(num)
        if 1 <= days <= 30:
            return days
    
    return 5  # Default

def extract_travelers(user_input):
    """Extract number of travelers"""
    # Look for numbers
    numbers = re.findall(r'\d+', user_input)
    for num in numbers:
        travelers = int(num)
        if 1 <= travelers <= 20:  # Reasonable range
            return travelers
    
    # Check for common phrases
    if any(word in user_input for word in ['alone', 'solo', 'just me', 'myself']):
        return 1
    elif 'couple' in user_input or 'two of us' in user_input:
        return 2
    elif 'family' in user_input:
        return 4
    
    return 1  # Default

def extract_budget(user_input):
    """Extract budget preference"""
    if any(word in user_input for word in ['budget', 'cheap', 'economy', 'low cost', 'affordable', 'save money']):
        return 'budget'
    elif any(word in user_input for word in ['luxury', 'premium', 'expensive', 'high end', 'deluxe', 'five star']):
        return 'luxury'
    else:
        return 'moderate'  # Default

def extract_trip_type(user_input):
    """Extract trip type"""
    if any(word in user_input for word in ['adventure', 'hiking', 'trekking', 'outdoor', 'exploring']):
        return 'adventure'
    elif any(word in user_input for word in ['relax', 'beach', 'spa', 'wellness', 'peaceful', 'calm']):
        return 'relaxation'
    elif any(word in user_input for word in ['romantic', 'honeymoon', 'couple', 'anniversary']):
        return 'romantic'
    elif any(word in user_input for word in ['family', 'kids', 'children', 'child']):
        return 'family'
    elif any(word in user_input for word in ['business', 'work', 'corporate']):
        return 'business'
    elif any(word in user_input for word in ['cultural', 'heritage', 'historical', 'museum']):
        return 'cultural'
    else:
        return 'cultural'  # Default

def create_itinerary_from_voice_data(itinerary_data, user):
    """Create itinerary from voice-collected data"""
    # Create itinerary
    itinerary = Itinerary(
        user=user,
        title=f"Voice Planned Trip to {itinerary_data['destination']}",
        destination=itinerary_data['destination'],
        start_date=datetime.strptime(itinerary_data['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(itinerary_data['end_date'], '%Y-%m-%d').date(),
        budget=itinerary_data['budget'],
        trip_type=itinerary_data['trip_type'],
        travelers=itinerary_data['travelers'],
        special_requirements=itinerary_data.get('special_requirements', 'Created via voice assistant')
    )
    itinerary.save()
    
    # Generate AI itinerary
    ai_engine = TravelAI()
    ai_itinerary_data = {
        'destination': itinerary.destination,
        'duration': itinerary.duration(),
        'budget': itinerary.budget,
        'trip_type': itinerary.trip_type,
        'travelers': itinerary.travelers,
        'special_requirements': itinerary.special_requirements,
        'start_date': itinerary.start_date.isoformat()
    }
    
    ai_itinerary = ai_engine.generate_itinerary(ai_itinerary_data)
    
    # Save day plans
    for day_data in ai_itinerary.get('days', []):
        day_plan = DayPlan(
            itinerary=itinerary,
            day_number=day_data.get('day', 1),
            date=itinerary.start_date + timedelta(days=day_data.get('day', 1)-1),
            activities=day_data.get('activities', [])
        )
        day_plan.save()
    
    # Send email in background
    def send_email():
        try:
            send_itinerary_created_email(user, itinerary)
        except Exception as e:
            print(f"Email error: {e}")
    
    email_thread = Thread(target=send_email)
    email_thread.daemon = True
    email_thread.start()
    
    return itinerary

@login_required
def api_voice_start(request):
    """Start a new voice conversation"""
    request.session['conversation_step'] = 'welcome'
    request.session['itinerary_data'] = {}
    
    welcome_message = "🎤 Hello! I'm your travel assistant. I can help you create a perfect travel itinerary. Would you like to plan a new trip? Say yes to continue or no to cancel."
    speak_text(welcome_message)
    
    return JsonResponse({
        'success': True,
        'message': welcome_message,
        'next_step': 'welcome'
    })

@login_required
def api_voice_status(request):
    """Get current conversation status"""
    return JsonResponse({
        'conversation_step': request.session.get('conversation_step', 'welcome'),
        'itinerary_data': request.session.get('itinerary_data', {})
    })

@login_required
def voice_create_itinerary(request):
    """Voice-guided itinerary creation"""
    if request.method == 'POST':
        # Process voice-collected data
        itinerary_data = request.POST.get('itinerary_data')
        if itinerary_data:
            try:
                data = json.loads(itinerary_data)
                
                # Create itinerary
                itinerary = Itinerary(
                    user=request.user,
                    title=data.get('title', f"🎤 Voice Planned Trip to {data.get('destination', 'Unknown')}"),
                    destination=data.get('destination', ''),
                    start_date=datetime.strptime(data.get('start_date'), '%Y-%m-%d').date(),
                    end_date=datetime.strptime(data.get('end_date'), '%Y-%m-%d').date(),
                    budget=data.get('budget', 'moderate'),
                    trip_type=data.get('trip_type', 'cultural'),
                    travelers=data.get('travelers', 1),
                    special_requirements=data.get('special_requirements', '')
                )
                itinerary.save()
                
                # Generate AI itinerary
                ai_engine = TravelAI()
                ai_itinerary = ai_engine.generate_itinerary({
                    'destination': itinerary.destination,
                    'duration': itinerary.duration(),
                    'budget': itinerary.budget,
                    'trip_type': itinerary.trip_type,
                    'travelers': itinerary.travelers,
                    'special_requirements': itinerary.special_requirements,
                    'start_date': itinerary.start_date.isoformat()
                })
                
                # Save day plans
                for day_data in ai_itinerary.get('days', []):
                    day_plan = DayPlan(
                        itinerary=itinerary,
                        day_number=day_data.get('day', 1),
                        date=itinerary.start_date + timedelta(days=day_data.get('day', 1)-1),
                        activities=day_data.get('activities', [])
                    )
                    day_plan.save()
                
                # Send email
                def send_email():
                    try:
                        send_itinerary_created_email(request.user, itinerary)
                    except Exception as e:
                        print(f"Email error: {e}")
                
                email_thread = Thread(target=send_email)
                email_thread.daemon = True
                email_thread.start()
                
                messages.success(request, '🎉 Itinerary created successfully via voice!')
                speak_text("🎤 Your itinerary has been created successfully! I've sent the details to your email.")
                return redirect('itinerary_detail', pk=itinerary.pk)
                
            except Exception as e:
                messages.error(request, f'❌ Error creating itinerary: {str(e)}')
                return redirect('voice_assistant')
    
    return render(request, 'planner/voice_create.html')

@login_required
def export_itinerary_pdf(request, pk):
    """Export itinerary as PDF"""
    itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
    
    # This would integrate with a PDF generation library like ReportLab
    # For now, return a JSON response
    return JsonResponse({
        'success': True,
        'message': '📄 PDF export feature coming soon!',
        'itinerary': itinerary.title
    })

@login_required
def share_itinerary(request, pk):
    """Share itinerary via email or link"""
    itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        # Here you would implement actual sharing logic
        messages.success(request, f'📧 Itinerary shared with {email}')
        return redirect('itinerary_detail', pk=pk)
    
    return render(request, 'planner/share_itinerary.html', {'itinerary': itinerary})

@login_required
def api_voice_conversation(request):
    """Handle real-time voice conversation"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('text', '').lower()
            conversation_step = data.get('conversation_step', 'welcome')
            itinerary_data = request.session.get('itinerary_data', {})
            
            # Process the conversation
            response = handle_conversation_step(conversation_step, user_input, itinerary_data, request.user)
            
            # Update session state
            request.session['conversation_step'] = response.get('next_step', conversation_step)
            request.session['itinerary_data'] = response.get('updated_data', itinerary_data)
            
            return JsonResponse({
                'success': True,
                'response': response
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})