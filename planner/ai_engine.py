import openai
import json
import os
import requests
from datetime import datetime, timedelta
import random

class TravelAI:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY', '')  # Optional
        if self.api_key:
            openai.api_key = self.api_key
    
    def get_location_image(self, activity_name, location, activity_type, destination):
        """Get relevant image based on activity type and location"""
        try:
            # Create more specific search queries based on activity type
            search_terms = self._get_image_search_terms(activity_name, location, activity_type, destination)
            
            # Try Unsplash API first if key is available
            if self.unsplash_access_key:
                for query in search_terms:
                    image_url = self._try_unsplash_search(query)
                    if image_url:
                        return image_url
            
            # Fallback to curated placeholder images based on activity type
            return self._get_curated_placeholder_image(activity_name, activity_type, destination)
            
        except Exception as e:
            print(f"Image API error: {e}")
            return self._get_curated_placeholder_image(activity_name, activity_type, destination)
    
    def _get_image_search_terms(self, activity_name, location, activity_type, destination):
        """Generate relevant search terms for images"""
        terms = []
        
        # Primary search term combinations
        terms.append(f"{activity_name} {location} {destination}")
        terms.append(f"{activity_name} {destination}")
        
        # Activity-type specific terms
        activity_terms = {
            'cultural': [f"{destination} cultural experience", f"{location} traditional", "cultural workshop"],
            'sightseeing': [f"{destination} landmarks", f"{location} scenery", "tourist attraction"],
            'adventure': [f"{destination} adventure", "outdoor activities", "hiking trail"],
            'dining': [f"{destination} food", "local cuisine", "restaurant interior"],
            'shopping': [f"{destination} shopping", "local market", "boutique store"],
            'relaxation': [f"{destination} spa", "wellness retreat", "peaceful scenery"],
            'beach': [f"{destination} beach", "ocean view", "coastal scenery"],
            'hiking': [f"{destination} hiking", "mountain trail", "nature walk"],
            'sports': [f"{destination} sports", "adventure sports", "outdoor activities"],
            'wellness': [f"{destination} wellness", "spa retreat", "meditation"]
        }
        
        # Add activity-specific terms
        if activity_type in activity_terms:
            terms.extend(activity_terms[activity_type])
        
        # Add location-specific terms
        terms.append(f"{location} {destination}")
        terms.append(f"{destination} travel")
        
        return terms
    
    def _try_unsplash_search(self, query):
        """Try to get image from Unsplash"""
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': query,
                'per_page': 1,
                'client_id': self.unsplash_access_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    return data['results'][0]['urls']['regular']
        except:
            pass
        return None
    
    def _get_curated_placeholder_image(self, activity_name, activity_type, destination):
        """Get curated placeholder images based on activity type"""
        base_url = "https://picsum.photos/600/400"
        
        # Create a consistent seed based on activity and destination
        seed_text = f"{activity_name}{activity_type}{destination}"
        seed = hash(seed_text) % 1000
        
        return f"{base_url}?random={seed}"
    
    def generate_itinerary(self, itinerary_data):
        """Generate itinerary using AI with relevant images"""
        
        if not self.api_key:
            return self._generate_enhanced_fallback_itinerary(itinerary_data)
        
        prompt = self._build_prompt(itinerary_data)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional travel planner. Create detailed, realistic travel itineraries with specific locations and activities. Include specific landmarks, restaurants, and attractions that actually exist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # Increased temperature for more creativity
                max_tokens=3000   # Increased tokens for more detailed responses
            )
            
            itinerary_text = response.choices[0].message.content
            parsed_itinerary = self._parse_ai_response(itinerary_text, itinerary_data)
            
            # Add relevant images to activities
            for day_data in parsed_itinerary.get('days', []):
                for activity in day_data.get('activities', []):
                    location = activity.get('location', '')
                    activity_name = activity.get('activity', '')
                    activity_type = activity.get('type', 'sightseeing')
                    
                    if location and activity_name:
                        activity['image_url'] = self.get_location_image(
                            activity_name, 
                            location,
                            activity_type,
                            itinerary_data['destination']
                        )
            
            return parsed_itinerary
            
        except Exception as e:
            print(f"AI API error: {e}")
            return self._generate_enhanced_fallback_itinerary(itinerary_data)
    
    def _build_prompt(self, itinerary_data):
        destination = itinerary_data['destination']
        duration = itinerary_data['duration']
        budget = itinerary_data['budget']
        trip_type = itinerary_data['trip_type']
        travelers = itinerary_data['travelers']
        children_count = itinerary_data.get('children_count', 0)
        children_friendly = itinerary_data.get('children_friendly', False)
        activity_preferences = itinerary_data.get('activity_preferences', [])
        requirements = itinerary_data.get('special_requirements', '')
        
        prompt = f"""
        Create a detailed {duration}-day travel itinerary for {destination}.
        
        TRIP DETAILS:
        - Destination: {destination}
        - Duration: {duration} days
        - Budget: {budget}
        - Trip Type: {trip_type}
        - Travelers: {travelers} adults, {children_count} children
        - Children Friendly: {children_friendly}
        - Activity Preferences: {', '.join(activity_preferences) if activity_preferences else 'None specified'}
        - Special Requirements: {requirements}
        
        IMPORTANT REQUIREMENTS:
        1. Create UNIQUE activities for each day - no repeating the same activities
        2. Include SPECIFIC, REAL locations and landmarks in {destination}
        3. Provide VARIED pro tips for each activity (not generic advice)
        4. Include realistic weather considerations based on typical conditions in {destination}
        5. Activities should match the {trip_type} trip style
        6. Consider {budget} budget level for costs
        7. Make activities children-friendly if needed: {children_friendly}
        8. Incorporate these activity preferences: {activity_preferences}
        
        FORMAT REQUIREMENTS:
        {{
            "days": [
                {{
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": [
                        {{
                            "time": "09:00 AM",
                            "activity": "Specific, unique activity name",
                            "description": "Detailed description mentioning specific locations",
                            "type": "sightseeing/dining/adventure/shopping/relaxation/cultural/beach/hiking/sports/wellness",
                            "duration_minutes": 120,
                            "cost_estimate": 50.00,
                            "location": "Specific real location in {destination}",
                            "opening_hours": "Realistic opening hours",
                            "entrance_fee": "Realistic entrance fee",
                            "children_friendly": true/false,
                            "tips": "Unique, specific tip for this exact activity",
                            "best_photo_spots": "Specific photo locations",
                            "weather_note": "Weather consideration specific to this activity",
                            "accessibility": "Accessibility information if relevant"
                        }}
                    ]
                }}
            ]
        }}
        
        EXAMPLE FOR SYDNEY, AUSTRALIA:
        - Activity: "Sydney Opera House Tour"
        - Location: "Bennelong Point, Sydney NSW 2000"
        - Tip: "Book the backstage tour for a unique behind-the-scenes experience"
        - Weather: "The harbor can be windy, bring a light jacket"
        
        Make each day unique and engaging!
        """
        
        return prompt
    
    def _parse_ai_response(self, response_text, itinerary_data):
        """Parse AI response and convert to structured data"""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                itinerary_json = json.loads(json_str)
                return itinerary_json
        except:
            pass
        
        return self._generate_enhanced_fallback_itinerary(itinerary_data)
    
    def _generate_enhanced_fallback_itinerary(self, itinerary_data):
        """Generate a much better fallback itinerary with specific locations"""
        destination = itinerary_data['destination']
        duration = itinerary_data['duration']
        trip_type = itinerary_data['trip_type']
        budget = itinerary_data['budget']
        travelers = itinerary_data.get('travelers', 1)
        children_count = itinerary_data.get('children_count', 0)
        children_friendly = itinerary_data.get('children_friendly', False)
        activity_preferences = itinerary_data.get('activity_preferences', [])
        
        print(f"🔄 Using enhanced fallback itinerary for {destination}")
        
        # Destination-specific activity templates
        destination_activities = self._get_destination_specific_activities(destination, trip_type, activity_preferences)
        
        days = []
        for day in range(1, duration + 1):
            day_activities = []
            
            # Morning activity
            morning_activity = self._get_unique_activity(destination, day, 'morning', trip_type, budget, children_friendly, destination_activities)
            day_activities.append(morning_activity)
            
            # Afternoon activity  
            afternoon_activity = self._get_unique_activity(destination, day, 'afternoon', trip_type, budget, children_friendly, destination_activities)
            day_activities.append(afternoon_activity)
            
            # Evening activity
            evening_activity = self._get_unique_activity(destination, day, 'evening', trip_type, budget, children_friendly, destination_activities)
            day_activities.append(evening_activity)
            
            days.append({
                "day": day,
                "date": itinerary_data.get('start_date', '2024-01-01'),
                "activities": day_activities
            })
        
        return {"days": days}
    
    def _get_destination_specific_activities(self, destination, trip_type, activity_preferences):
        """Get destination-specific activity templates"""
        destination_lower = destination.lower()
        
        # Common activities for major destinations
        if 'sydney' in destination_lower or 'australia' in destination_lower:
            return {
                'landmarks': [
                    "Sydney Opera House", "Sydney Harbour Bridge", "Bondi Beach", 
                    "Royal Botanic Garden", "Taronga Zoo", "The Rocks", "Darling Harbour"
                ],
                'museums': [
                    "Australian Museum", "Museum of Contemporary Art", "Hyde Park Barracks Museum"
                ],
                'cultural': [
                    "Aboriginal Heritage Tour", "Sydney Fish Market", "Paddy's Markets"
                ],
                'nature': [
                    "Blue Mountains day trip", "Coastal walk from Bondi to Coogee", "Manly Beach"
                ],
                'food': [
                    "Sydney Seafood School", "The Grounds of Alexandria", "Chinatown food tour"
                ]
            }
        elif 'paris' in destination_lower or 'france' in destination_lower:
            return {
                'landmarks': ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Arc de Triomphe"],
                'museums': ["Musée d'Orsay", "Centre Pompidou", "Rodin Museum"],
                'cultural': ["Montmartre artists square", "Seine River cruise", "Latin Quarter"],
                'food': ["French pastry class", "Wine tasting", "Cheese market visit"]
            }
        elif 'tokyo' in destination_lower or 'japan' in destination_lower:
            return {
                'landmarks': ["Tokyo Skytree", "Sensoji Temple", "Meiji Shrine", "Imperial Palace"],
                'cultural': ["Tsukiji Fish Market", "Harajuku fashion district", "Traditional tea ceremony"],
                'shopping': ["Ginza district", "Akihabara electric town", "Shibuya shopping"]
            }
        else:
            # Generic but varied activities for unknown destinations
            return {
                'landmarks': [
                    f"Historic City Center of {destination}", 
                    f"Main Cathedral of {destination}",
                    f"Central Park of {destination}",
                    f"Old Town District"
                ],
                'cultural': [
                    f"Local Market in {destination}",
                    f"Traditional Craft Workshop",
                    f"Cultural Performance Venue",
                    f"Historical Museum of {destination}"
                ],
                'nature': [
                    f"Botanical Gardens",
                    f"Riverfront Walk",
                    f"Mountain Viewpoint",
                    f"Beach Promenade"
                ],
                'food': [
                    f"Local Cuisine Cooking Class",
                    f"Food Market Tour",
                    f"Traditional Restaurant Experience",
                    f"Street Food Exploration"
                ]
            }
    
    def _get_unique_activity(self, destination, day, time_of_day, trip_type, budget, children_friendly, destination_activities):
        """Generate a unique activity for the specific day and time"""
        
        # Cost based on budget
        cost_ranges = {
            'budget': (15, 40),
            'moderate': (35, 80), 
            'luxury': (75, 200)
        }
        cost_min, cost_max = cost_ranges.get(budget, (25, 60))
        
        # Activity types based on time of day
        time_activities = {
            'morning': ['sightseeing', 'cultural', 'adventure', 'hiking'],
            'afternoon': ['sightseeing', 'shopping', 'food', 'cultural', 'beach'],
            'evening': ['dining', 'nightlife', 'cultural', 'relaxation']
        }
        
        activity_type = random.choice(time_activities[time_of_day])
        
        # Get specific activity details
        activity_details = self._get_activity_details(destination, activity_type, day, destination_activities)
        
        # Time slots
        time_slots = {
            'morning': ["08:00 AM", "09:00 AM", "10:00 AM"],
            'afternoon': ["01:00 PM", "02:00 PM", "03:00 PM"], 
            'evening': ["06:00 PM", "07:00 PM", "08:00 PM"]
        }
        
        return {
            "time": random.choice(time_slots[time_of_day]),
            "activity": activity_details['name'],
            "description": activity_details['description'],
            "type": activity_type,
            "duration_minutes": random.choice([90, 120, 150, 180]),
            "cost_estimate": round(random.uniform(cost_min, cost_max), 2),
            "location": activity_details['location'],
            "opening_hours": activity_details.get('opening_hours', '9:00 AM - 6:00 PM'),
            "entrance_fee": activity_details.get('entrance_fee', 'Varies'),
            "children_friendly": children_friendly,
            "tips": activity_details['tip'],
            "best_photo_spots": activity_details.get('photo_spot', 'Main area with good views'),
            "weather_note": activity_details.get('weather_note', 'Check local weather conditions'),
            "image_url": self.get_location_image(
                activity_details['name'], 
                activity_details['location'],
                activity_type,
                destination
            )
        }
    
    def _get_activity_details(self, destination, activity_type, day, destination_activities):
        """Get specific activity details"""
        
        activity_templates = {
            'sightseeing': [
                {
                    'name': f"Explore {random.choice(destination_activities.get('landmarks', [f'Historic Center of {destination}']))}",
                    'description': f"Discover the fascinating history and architecture of this iconic {destination} landmark",
                    'location': random.choice(destination_activities.get('landmarks', [f'City Center, {destination}'])),
                    'tip': f"Visit early to avoid crowds and get the best photo opportunities",
                    'weather_note': 'Perfect for clear days, bring sunscreen'
                }
            ],
            'cultural': [
                {
                    'name': f"Cultural Experience at {random.choice(destination_activities.get('cultural', [f'Cultural Center of {destination}']))}",
                    'description': f"Immerse yourself in the local culture and traditions of {destination}",
                    'location': random.choice(destination_activities.get('cultural', [f'Cultural District, {destination}'])),
                    'tip': f"Try to interact with local artisans for a more authentic experience",
                    'weather_note': 'Mostly indoor activity, suitable for any weather'
                }
            ],
            'dining': [
                {
                    'name': f"Local Food Adventure in {destination}",
                    'description': f"Taste authentic local cuisine and discover hidden culinary gems",
                    'location': random.choice(destination_activities.get('food', [f'Food District, {destination}'])),
                    'tip': f"Ask locals for their favorite dishes and restaurants",
                    'weather_note': 'Indoor dining, comfortable in any weather'
                }
            ],
            'shopping': [
                {
                    'name': f"Shopping at {destination}'s Markets",
                    'description': f"Find unique souvenirs and local products at traditional markets",
                    'location': f"Shopping District, {destination}",
                    'tip': f"Don't be afraid to bargain at local markets for better prices",
                    'weather_note': 'Markets are often covered, suitable for most weather'
                }
            ],
            'adventure': [
                {
                    'name': f"Outdoor Adventure in {destination}",
                    'description': f"Experience the natural beauty and adventure activities around {destination}",
                    'location': f"Natural Park, {destination}",
                    'tip': f"Wear comfortable shoes and bring water for this active experience",
                    'weather_note': 'Best enjoyed in good weather conditions'
                }
            ],
            'beach': [
                {
                    'name': f"Beach Day in {destination}",
                    'description': f"Relax and enjoy the beautiful coastal scenery of {destination}",
                    'location': f"Main Beach, {destination}",
                    'tip': f"Arrive early to get a good spot and avoid the midday sun",
                    'weather_note': 'Perfect for sunny days, check tide schedules'
                }
            ],
            'relaxation': [
                {
                    'name': f"Wellness and Relaxation in {destination}",
                    'description': f"Pamper yourself with local wellness treatments and relaxation activities",
                    'location': f"Wellness Center, {destination}",
                    'tip': f"Book treatments in advance for the best availability",
                    'weather_note': 'Indoor activity, suitable for any weather'
                }
            ],
            'hiking': [
                {
                    'name': f"Scenic Hike around {destination}",
                    'description': f"Explore natural trails and enjoy breathtaking views of the surrounding area",
                    'location': f"Mountain Trail, {destination}",
                    'tip': f"Bring proper hiking gear and check trail conditions before starting",
                    'weather_note': 'Avoid hiking in rainy or stormy conditions'
                }
            ],
            'sports': [
                {
                    'name': f"Sports Activity in {destination}",
                    'description': f"Engage in local sports and recreational activities",
                    'location': f"Sports Complex, {destination}",
                    'tip': f"Book equipment rental in advance for the best selection",
                    'weather_note': 'Weather-dependent activity'
                }
            ],
            'wellness': [
                {
                    'name': f"Wellness Retreat in {destination}",
                    'description': f"Rejuvenate with spa treatments and wellness practices",
                    'location': f"Spa Resort, {destination}",
                    'tip': f"Arrive early to enjoy all the facilities",
                    'weather_note': 'Indoor activity, perfect for any weather'
                }
            ]
        }
        
        # Return a random activity from the appropriate category
        activities = activity_templates.get(activity_type, activity_templates['sightseeing'])
        activity = random.choice(activities)
        
        # Make it more unique for each day
        activity['name'] = activity['name'].replace("Explore", ["Guided Tour of", "Discovery of", "Visit to"][day % 3])
        activity['tip'] = activity['tip'] + f" - Day {day} specific advice"
        
        return activity