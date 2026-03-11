from django.db import models
from django.contrib.auth.models import User
import json
import random
import string
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse

class OTPVerification(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
    
    def generate_otp(self):
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = self.generate_otp()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.email} - {self.otp_code}"

    class Meta:
        verbose_name = "🔐 OTP Verification"
        verbose_name_plural = "🔐 OTP Verifications"

class Itinerary(models.Model):
    BUDGET_CHOICES = [
        ('budget', '💰 Budget ($0 - $1000)'),
        ('moderate', '💸 Moderate ($1000 - $3000)'),
        ('luxury', '💎 Luxury ($3000+)'),
    ]
    
    TRIP_TYPE_CHOICES = [
        ('adventure', '🏔️ Adventure'),
        ('relaxation', '🏖️ Relaxation'),
        ('cultural', '🏛️ Cultural'),
        ('romantic', '💖 Romantic'),
        ('family', '👨‍👩‍👧‍👦 Family'),
        ('business', '💼 Business'),
        ('solo', '🧳 Solo Travel'),
    ]
    
    ACTIVITY_PREFERENCES = [
        ('hiking', '🥾 Hiking & Trekking'),
        ('beach', '🏖️ Beach Activities'),
        ('shopping', '🛍️ Shopping'),
        ('sightseeing', '📸 Sightseeing'),
        ('food', '🍽️ Food & Dining'),
        ('nightlife', '🌃 Nightlife & Entertainment'),
        ('museums', '🏛️ Museums & Galleries'),
        ('sports', '⚽ Sports & Adventure'),
        ('wellness', '🧘 Wellness & Spa'),
        ('wildlife', '🐘 Wildlife & Nature'),
        ('photography', '📷 Photography'),
        ('local_culture', '🎎 Local Culture'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.CharField(max_length=20, choices=BUDGET_CHOICES)
    trip_type = models.CharField(max_length=20, choices=TRIP_TYPE_CHOICES)
    travelers = models.IntegerField(default=1)
    children_count = models.IntegerField(default=0, verbose_name="👶 Number of Children")
    children_friendly = models.BooleanField(default=False, verbose_name="👶 Children Friendly")
    activity_preferences = models.JSONField(default=list, blank=True, help_text="Selected activity preferences")
    special_requirements = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False, verbose_name="🌐 Public Itinerary")
    featured_image = models.URLField(blank=True, verbose_name="🖼️ Featured Image")
    
    def duration(self):
        return (self.end_date - self.start_date).days + 1
    
    def get_activity_preferences_display(self):
        activity_map = dict(self.ACTIVITY_PREFERENCES)
        return [activity_map.get(pref, pref) for pref in self.activity_preferences]
    
    def total_travelers(self):
        return self.travelers + self.children_count
    
    def get_absolute_url(self):
        return reverse('itinerary_detail', kwargs={'pk': self.pk})
    
    def total_estimated_cost(self):
        """Calculate total estimated cost from all activities"""
        total = 0
        for day in self.days.all():
            for activity in day.activities:
                total += activity.get('cost_estimate', 0)
        return total
    
    def activities_count(self):
        """Count total activities"""
        count = 0
        for day in self.days.all():
            count += len(day.activities)
        return count
    
    def __str__(self):
        return f"✈️ {self.title} - {self.destination}"

    class Meta:
        verbose_name = "📅 Itinerary"
        verbose_name_plural = "📅 Itineraries"
        ordering = ['-created_at']

class Destination(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    popularity_score = models.IntegerField(default=0, verbose_name="⭐ Popularity Score")
    best_season = models.CharField(max_length=100, blank=True, verbose_name="🌞 Best Season to Visit")
    image_url = models.URLField(blank=True, verbose_name="🖼️ Destination Image")
    
    def __str__(self):
        return f"📍 {self.name}, {self.country}"

    class Meta:
        verbose_name = "📍 Destination"
        verbose_name_plural = "📍 Destinations"
        ordering = ['name']

class DayPlan(models.Model):
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name='days')
    day_number = models.IntegerField()
    date = models.DateField()
    activities = models.JSONField()
    weather_forecast = models.JSONField(blank=True, null=True, verbose_name="🌤️ Weather Forecast")
    notes = models.TextField(blank=True, verbose_name="📝 Day Notes")
    
    class Meta:
        ordering = ['day_number']
        verbose_name = "📋 Day Plan"
        verbose_name_plural = "📋 Day Plans"
    
    def __str__(self):
        return f"📅 Day {self.day_number} - {self.itinerary.title}"
    
    def get_activities_count(self):
        return len(self.activities) if self.activities else 0
    
    def get_total_cost(self):
        total = 0
        if self.activities:
            for activity in self.activities:
                total += activity.get('cost_estimate', 0)
        return total
    
    def get_day_themes(self):
        """Extract themes from day's activities"""
        themes = set()
        if self.activities:
            for activity in self.activities:
                themes.add(activity.get('type', 'general'))
        return list(themes)

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('sightseeing', '📸 Sightseeing'),
        ('dining', '🍽️ Dining'),
        ('adventure', '🧗 Adventure'),
        ('shopping', '🛍️ Shopping'),
        ('relaxation', '🧘 Relaxation'),
        ('cultural', '🏛️ Cultural'),
        ('beach', '🏖️ Beach'),
        ('hiking', '🥾 Hiking'),
        ('sports', '⚽ Sports'),
        ('wellness', '💆 Wellness'),
        ('transport', '🚗 Transport'),
        ('accommodation', '🏨 Accommodation'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    duration_minutes = models.IntegerField()
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    location = models.CharField(max_length=200, blank=True)
    children_friendly = models.BooleanField(default=False)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('easy', '🟢 Easy'),
        ('moderate', '🟡 Moderate'),
        ('difficult', '🔴 Difficult')
    ], default='easy')
    booking_url = models.URLField(blank=True, verbose_name="🔗 Booking URL")
    image_url = models.URLField(blank=True, verbose_name="🖼️ Activity Image")
    
    def __str__(self):
        return f"🎯 {self.name}"

    class Meta:
        verbose_name = "🎯 Activity"
        verbose_name_plural = "🎯 Activities"
        ordering = ['name']

class TravelTip(models.Model):
    CATEGORY_CHOICES = [
        ('packing', '🎒 Packing'),
        ('budget', '💰 Budget'),
        ('safety', '🛡️ Safety'),
        ('transport', '🚗 Transport'),
        ('food', '🍽️ Food'),
        ('culture', '🎎 Culture'),
        ('technology', '📱 Technology'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"💡 {self.title}"

    class Meta:
        verbose_name = "💡 Travel Tip"
        verbose_name_plural = "💡 Travel Tips"
        ordering = ['-created_at']