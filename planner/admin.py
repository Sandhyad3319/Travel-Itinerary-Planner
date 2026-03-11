from django.contrib import admin
from .models import Destination, Itinerary, DayPlan, Activity, OTPVerification

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp_code', 'created_at', 'is_verified', 'is_expired']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['email', 'otp_code']
    readonly_fields = ['created_at']
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'description_short']
    list_filter = ['country']
    search_fields = ['name', 'country']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

@admin.register(Itinerary)
class ItineraryAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'destination', 'start_date', 'end_date', 'budget', 'trip_type']
    list_filter = ['budget', 'trip_type', 'start_date']
    search_fields = ['title', 'user__username', 'destination']
    date_hierarchy = 'start_date'

@admin.register(DayPlan)
class DayPlanAdmin(admin.ModelAdmin):
    list_display = ['itinerary', 'day_number', 'date', 'activities_count']
    list_filter = ['itinerary']
    
    def activities_count(self, obj):
        return obj.get_activities_count()
    activities_count.short_description = 'Activities'

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['name', 'activity_type', 'duration_minutes', 'cost_estimate']
    list_filter = ['activity_type']
    search_fields = ['name', 'description']