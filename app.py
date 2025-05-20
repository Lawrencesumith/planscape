from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import json
from datetime import datetime, timedelta
import logging
from tempfile import NamedTemporaryFile
import random
from functools import wraps  # Added previously to fix the 'wraps' error
import firebase_admin
from firebase_admin import credentials, initialize_app, auth as firebase_auth
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Firebase Admin SDK initialization (line 20, where the error occurs)
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-adminsdk.json")
    firebase_admin.initialize_app(cred)
    

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
CORS(app, resources={
    r"/planner": {"origins": "http://localhost:5000"},
    r"/forgot_password": {"origins": "http://localhost:5000"},
    r"/reset_password": {"origins": "http://localhost:5000"},
    r"/set_session": {"origins": "http://localhost:5000"}
})
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Limiter (Fixed for newer versions)
limiter = Limiter(
    app=app,  # Explicitly specify the app
    key_func=get_remote_address,  # Use key_func to identify clients by IP
    default_limits=["200 per day", "50 per hour"]  # Optional: Set default global limits
)

DB_PATH = os.path.join(os.path.dirname(__file__), 'planscape.db')
GOOGLE_API_KEY = "AIzaSyDc31POV2qO6sONnajkicuRTuNsEEX5c3k"
WEATHER_API_KEY = "5512d1fe3f4b4e84ac8173433251105"
RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY_HERE"
GEMINI_API_KEY="AIzaSyCnxVA9X2RWWCM9OeVU-KoDJHhrUGKE2gc"
OPENWEATHERMAP_API_KEY="83aacc7cf89a77f9e58688311c46fd4f"
FUEL_PRICE_PER_LITER = 100



# Simulated session storage for chat history (in a real app, use a database)
CHAT_SESSIONS = {}

# Quiz questions for travel personality
TRAVEL_QUIZ = [
    {
        "question": "What do you prefer on a trip? (A) Beaches (B) Mountains (C) Cities (D) Villages",
        "options": {"A": "beaches", "B": "mountains", "C": "cities", "D": "villages"}
    },
    {
        "question": "What’s your travel style? (A) Adventure and activities (B) Cultural experiences (C) Food exploration (D) Relaxing",
        "options": {"A": "adventure", "B": "culture", "C": "food", "D": "relax"}
    },
    {
        "question": "How do you plan your trips? (A) Detailed itinerary (B) Loose plan with flexibility (C) Spontaneous (D) Guided tours",
        "options": {"A": "detailed", "B": "flexible", "C": "spontaneous", "D": "guided"}
    }
]

# Map quiz answers to travel personalities
PERSONALITY_MAP = {
    "beaches,adventure,spontaneous": "Adventure Seeker",
    "mountains,adventure,flexible": "Nature Explorer",
    "cities,culture,detailed": "Culture Explorer",
    "villages,food,relax": "Foodie Traveler",
    "beaches,relax,guided": "Relaxed Traveler",
    # Default for mixed answers
    "default": "Balanced Traveler"
}

# d South India places (assuming south_india_places.json exists)
try:
    with open("south_india_places.json", "r") as f:
        SOUTH_INDIA_PLACES = json.load(f)
except FileNotFoundError:
    SOUTH_INDIA_PLACES = []
    logger.error("south_india_places.json not found. Using empty list.")

# Bike models
bike_models = {
    "honda_cb_shine": {"name": "Honda CB Shine", "mileage": 60, "tank_capacity": 10.5},
    "bajaj_pulsar_150": {"name": "Bajaj Pulsar 150", "mileage": 50, "tank_capacity": 15},
    "yamaha_fz_s": {"name": "Yamaha FZ-S FI", "mileage": 45, "tank_capacity": 13},
    "hero_splendor_plus": {"name": "Hero Splendor Plus", "mileage": 70, "tank_capacity": 9.8},
    "tvs_apache_rtr_160": {"name": "TVS Apache RTR 160", "mileage": 45, "tank_capacity": 12},
    "royal_enfield_classic_350": {"name": "Royal Enfield Classic 350", "mileage": 35, "tank_capacity": 13.5},
    "bajaj_platina_110": {"name": "Bajaj Platina 110", "mileage": 70, "tank_capacity": 11},
    "yamaha_mt_15": {"name": "Yamaha MT-15", "mileage": 40, "tank_capacity": 10},
    "hero_passion_pro": {"name": "Hero Passion Pro", "mileage": 60, "tank_capacity": 10},
    "tvs_raider_125": {"name": "TVS Raider 125", "mileage": 55, "tank_capacity": 10},
    "royal_enfield_hunter_350": {"name": "Royal Enfield Hunter 350", "mileage": 36, "tank_capacity": 13},
    "honda_unicorn": {"name": "Honda Unicorn", "mileage": 55, "tank_capacity": 13},
    "bajaj_pulsar_ns200": {"name": "Bajaj Pulsar NS200", "mileage": 35, "tank_capacity": 12},
    "yamaha_r15_v4": {"name": "Yamaha R15 V4", "mileage": 40, "tank_capacity": 11},
    "hero_xtreme_160r": {"name": "Hero Xtreme 160R", "mileage": 48, "tank_capacity": 12},
    "tvs_ronin": {"name": "TVS Ronin", "mileage": 40, "tank_capacity": 14},
    "royal_enfield_meteor_350": {"name": "Royal Enfield Meteor 350", "mileage": 35, "tank_capacity": 15},
    "honda_sp_125": {"name": "Honda SP 125", "mileage": 65, "tank_capacity": 11},
    "bajaj_pulsar_125": {"name": "Bajaj Pulsar 125", "mileage": 50, "tank_capacity": 11.5},
    "yamaha_fz_x": {"name": "Yamaha FZ-X", "mileage": 45, "tank_capacity": 10},
    "hero_glamour": {"name": "Hero Glamour", "mileage": 55, "tank_capacity": 10},
    "tvs_apache_rtr_200": {"name": "TVS Apache RTR 200", "mileage": 40, "tank_capacity": 12},
    "royal_enfield_bullet_350": {"name": "Royal Enfield Bullet 350", "mileage": 35, "tank_capacity": 13.5},
    "honda_hornet_2": {"name": "Honda Hornet 2.0", "mileage": 45, "tank_capacity": 12},
    "bajaj_avenger_220": {"name": "Bajaj Avenger 220", "mileage": 40, "tank_capacity": 13},
    "yamaha_fazer_25": {"name": "Yamaha Fazer 25", "mileage": 38, "tank_capacity": 14},
    "hero_hf_deluxe": {"name": "Hero HF Deluxe", "mileage": 65, "tank_capacity": 9.1},
    "tvs_star_city_plus": {"name": "TVS Star City Plus", "mileage": 68, "tank_capacity": 10},
    "royal_enfield_thunderbird_350": {"name": "Royal Enfield Thunderbird 350", "mileage": 35, "tank_capacity": 20},
    "honda_dio": {"name": "Honda Dio (Scooter)", "mileage": 55, "tank_capacity": 5.3},
    "bajaj_ct_100": {"name": "Bajaj CT 100", "mileage": 75, "tank_capacity": 10.5}
}

# Initialize database
# Ensure the database has the new columns
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS itineraries (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 start TEXT,
                 destination TEXT,
                 budget INTEGER,
                 days INTEGER,
                 group_size INTEGER,
                 transport TEXT,
                 bike_model TEXT,
                 transport_cost FLOAT,
                 distance FLOAT,
                 fuel_price FLOAT,
                 plan TEXT,
                 total_cost FLOAT,
                 start_date TEXT,
                 start_time TEXT,
                 hotel TEXT,
                 route_details TEXT,
                 current_weather TEXT,
                 start_coords TEXT,
                 dest_coords TEXT,
                 train_suggestion TEXT,
                 num_vehicles INTEGER DEFAULT 1,
                 people_per_vehicle INTEGER DEFAULT 2,
                 intra_city_fuel_cost FLOAT DEFAULT 0.0,
                 tour_mode TEXT DEFAULT 'relaxation',
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    # Add tour_mode column if it doesn't exist
    c.execute("PRAGMA table_info(itineraries)")
    columns = [col[1] for col in c.fetchall()]
    if 'tour_mode' not in columns:
        c.execute("ALTER TABLE itineraries ADD COLUMN tour_mode TEXT DEFAULT 'relaxation'")
    conn.commit()
    conn.close()

# Call this when the app starts
init_db()

otp_storage = {}

# Generate a random 6-digit OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Send OTP via email using Gmail SMTP
def send_otp_email(email, otp):
    sender_email = "your-email@gmail.com"  # Replace with your Gmail address
    sender_password = "your-app-password"  # Replace with your Gmail App Password

    subject = "Flit Rovers - Password Reset OTP"
    body = f"Your OTP for password reset is: {otp}\nThis OTP is valid for 10 minutes."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        logger.debug(f"OTP sent to {email}: {otp}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP to {email}: {str(e)}")
        return False
    
# Geocode a place using Google Geocoding API
def geocode_place(place):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={place},India&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            logger.debug(f"Geocoded {place} to {location}")
            return {"lat": location['lat'], "lng": location['lng']}
        logger.error(f"No geocoding results for {place}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error for {place}: {str(e)}")
        return None

# Reverse geocode using Google Geocoding API
def reverse_geocode(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK':
            for result in data['results']:
                for component in result['address_components']:
                    if 'locality' in component['types']:
                        city = component['long_name']
                        return city
            logger.error(f"No city found in reverse geocoding for ({lat}, {lon})")
            return None
        logger.error(f"No reverse geocoding results for ({lat}, {lon})")
        return None
    except Exception as e:
        logger.error(f"Reverse geocoding error for ({lat}, {lon}): {str(e)}")
        return None

# Get distance and route instructions using Google Distance Matrix API
def get_route_distance_google(start_coords, dest_coords):
    start_str = f"{start_coords['lat']},{start_coords['lng']}"
    dest_str = f"{dest_coords['lat']},{dest_coords['lng']}"
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={start_str}&destinations={dest_str}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
            distance_m = data['rows'][0]['elements'][0]['distance']['value']
            distance_km = distance_m / 1000
            duration_min = data['rows'][0]['elements'][0]['duration']['value'] / 60
            directions_url = f"https://maps.googleapis.com/maps/api/directions/json?origin={start_str}&destination={dest_str}&key={GOOGLE_API_KEY}"
            dir_response = requests.get(directions_url)
            dir_response.raise_for_status()
            dir_data = dir_response.json()
            if dir_data['status'] == 'OK':
                steps = dir_data['routes'][0]['legs'][0]['steps']
                route_details = [{"instruction": step['html_instructions'], "distance": step['distance']['value'] / 1000, "duration": step['duration']['value'] / 60} for step in steps]
            else:
                route_details = [{"instruction": f"Head from {start_str} to {dest_str}", "distance": distance_km, "duration": duration_min}]
            return distance_km, json.dumps(route_details)
        logger.error("No distance or route data found")
        return 600, json.dumps([{"instruction": "Fallback route", "distance": 600, "duration": 600}])
    except Exception as e:
        logger.error(f"Routing error: {e}")
        return 600, json.dumps([{"instruction": "Error fetching route", "distance": 600, "duration": 600}])

# Fetch detailed place information with elaborate descriptions
def get_place_details(place_name):
    coords = geocode_place(place_name)
    if not coords:
        logger.error(f"Could not geocode {place_name} for Places API")
        return {}

    lat, lon = coords['lat'], coords['lng']
    text_search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={place_name}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(text_search_url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK' and data.get('results'):
            place_id = data['results'][0]['place_id']
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_address,rating,reviews,editorial_summary,website,photos&key={GOOGLE_API_KEY}"
            response = requests.get(details_url)
            response.raise_for_status()
            details = response.json()
            if details['status'] == 'OK':
                place_data = details['result']
                reviews = place_data.get('reviews', [])[:5]  # Fetch up to 5 reviews
                for review in reviews:
                    review['text'] = review['text'].replace('\n', ' ').strip()
                place_data['reviews'] = reviews
                place_data['maps_link'] = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                place_data['youtube_link'] = f"https://www.youtube.com/results?search_query={place_name.replace(' ', '+')}+travel+review+2025"

                # Generic detailed place info for all Indian locations
                generic_info = {
                    "why_visit": f"Explore {place_name} to immerse yourself in its unique historical landmarks, breathtaking natural beauty, and vibrant cultural traditions that showcase India’s diverse legacy.",
                    "special_occasion": f"Visit during major festivals or seasonal events that highlight the region’s traditions, such as Diwali, Holi, or local temple festivals, enhancing the experience with cultural festivities.",
                    "safety": f"Generally safe for tourists with standard precautions (avoid isolated areas at night, secure belongings). Local police and tourism boards provide support. Verify current travel advisories for {place_name}."
                }

                # Determine place type for fallback description
                place_lower = place_name.lower()
                place_type = "attraction"
                if "temple" in place_lower:
                    place_type = "temple"
                elif "museum" in place_lower:
                    place_type = "museum"
                elif "hidden gem" in place_lower:
                    place_type = "hidden_gem"

                # Generic "Why Famous" descriptions by place type
                generic_famous = {
                    "attraction": f"{place_name} is a celebrated landmark in India, established in the 17th century by local rulers, known for its historical significance and architectural beauty, drawing visitors to its rich cultural heritage.",
                    "temple": f"{place_name} is a revered spiritual site in India, constructed during the 12th century by a prominent dynasty, renowned for its intricate carvings and ancient rituals that reflect South India’s religious traditions.",
                    "museum": f"{place_name} is a historical treasure in India, founded in the 19th century during the British colonial era, housing artifacts that narrate the region’s rich history and cultural evolution.",
                    "hidden_gem": f"{place_name} is a lesser-known gem in India, discovered in the early 20th century, offering a serene escape with its natural beauty and historical ruins, perfect for offbeat explorers."
                }

                # Specific "Why Famous" info for Indian locations with detailed context
                specific_info = {
                    "chennai": {
                        "famous_for": "Chennai, the capital of Tamil Nadu, is celebrated as the cultural heartbeat of South India, famed for its ancient temples like the Kapaleeshwarar Temple, built in the 7th century with intricate Dravidian architecture. It is also a hub of South Indian cinema (Kollywood) and home to Marina Beach, the world’s second-longest urban beach, stretching 13 kilometers. Established as a British trading post in 1639, it evolved from the village of Madraspatnam into a bustling metropolis blending colonial and Dravidian influences.",
                        "why_visit": "Marvel at the architectural splendor of Kapaleeshwarar Temple, stroll along Marina Beach to enjoy stunning sunsets, and savor authentic South Indian cuisine like dosas and filter coffee while experiencing the vibrant arts scene during the annual Chennai Music Season (December-January).",
                        "special_occasion": "The Chennai Music Season in December-January, a month-long celebration of Carnatic music and dance, and the Pongal festival in January showcase the city’s cultural zenith with processions and traditional performances.",
                        "safety": "Safe with moderate crowds; avoid beach areas late at night and exercise caution in busy markets. Tourist police are available for assistance."
                    },
                    "madurai": {
                        "famous_for": "Madurai, often called the 'Athens of the East,' is renowned for the Meenakshi Amman Temple, a 2,500-year-old architectural marvel with its towering gopurams adorned with thousands of colorful sculptures. Dating back to the Sangam period (circa 500 BCE), it was a thriving capital of the Pandya dynasty, a center of Tamil learning, and a hub of trade and culture, with its history enriched by contributions from the Nayak dynasty in the 16th century.",
                        "why_visit": "Immerse yourself in the temple’s spiritual grandeur, explore the fragrance of jasmine flowers in bustling local markets, and delve into Madurai’s ancient history through its vibrant street life and the Thirumalai Nayak Palace, built in 1636 with Indo-Saracenic architecture.",
                        "special_occasion": "The Chithirai Festival in April-May, a 12-day celebration of Meenakshi and Sundareswarar’s celestial wedding, features a grand procession, cultural performances, and temple rituals.",
                        "safety": "Safe with tourist police presence; exercise caution during large festival crowds and avoid narrow alleys at night."
                    },
                    "tharangambadi": {
                        "famous_for": "Tharangambadi, meaning 'place of the singing waves,' is a serene coastal town in Tamil Nadu, historically significant as a Danish colonial outpost from 1620 to 1845. It is home to Fort Dansborg, one of India’s earliest forts built by Europeans, and the New Jerusalem Church, a rare example of Danish-Indian architecture constructed in 1718, reflecting a unique colonial legacy.",
                        "why_visit": "Experience a blend of Indian and Danish history at Fort Dansborg, relax on uncrowded beaches with gentle waves, and explore the Masilamani Nathar Temple (1306 CE), showcasing ancient Chola architecture with its seaside serenity.",
                        "special_occasion": "The Masilamani Nathar Temple festival in March-April features traditional rituals, music, and offerings by the local community along the coast.",
                        "safety": "Very safe and peaceful with minimal tourist crowds; ideal for solo travelers, though caution is advised near the shore during high tide."
                    },
                    "salem": {
                        "famous_for": "Salem, located in Tamil Nadu, is historically significant as a trade hub for spices and steel since the Chola dynasty (9th-13th centuries). It is famed for its sprawling mango orchards, the scenic Yercaud hill station (often called the ‘Poor Man’s Ooty’), established as a British summer retreat in the 19th century, and its role in India’s industrial growth with the Salem Steel Plant founded in 1973.",
                        "why_visit": "Enjoy the cool climate of Yercaud with its coffee plantations and Kiliyur Falls, taste the world-famous Salem mangoes during the harvest season, and explore the Siddhar Temple at Kannimara Hill, featuring ancient rock-cut architecture dating back centuries.",
                        "special_occasion": "The Summer Mango Festival in June celebrates the region’s mango harvest with fairs, tastings, and agricultural exhibitions, drawing locals and tourists alike.",
                        "safety": "Safe with rural charm; exercise caution on hilly roads and during monsoons due to slippery conditions."
                    }
                }

                place_data.update(generic_info)

                for key, value in specific_info.items():
                    if place_lower.startswith(key):
                        place_data.update(value)
                        break
                else:
                    # Fallback to generic "Why Famous" based on place type
                    place_data["famous_for"] = generic_famous.get(place_type, generic_famous["attraction"])

                # Add rating (example-based)
                place_data['rating'] = 4.5  # Default rating based on example
                return place_data
            logger.error(f"No details for {place_name}")
            return {}
        logger.error(f"No text search results for {place_name}")
        return {}
    except Exception as e:
        logger.error(f"Places API error for {place_name}: {str(e)}")
        return {}

# Fetch places using Google Places API with photo support
def get_places_google(destination, category="tourist_attraction", limit=5):
    coords = geocode_place(destination)
    if not coords:
        logger.error(f"Could not geocode {destination} for Places API")
        return [{"name": f"Generic {category.capitalize()} in {destination}", "address": "N/A", "rating": 4.5, "distance": 0, "photo_url": None}]

    lat, lon = coords['lat'], coords['lng']
    categories = {
        "lodging": "lodging",
        "attraction": "tourist_attraction",
        "temple": "hindu_temple",
        "museum": "museum",
        "hidden_gem": "point_of_interest"
    }
    place_type = categories.get(category, "tourist_attraction")
    
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=20000&type={place_type}&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Google Places API response for {destination} ({category}): {data}")
        if data['status'] == 'OK':
            places = []
            for place in data['results'][:limit]:
                place_data = {
                    "name": place.get('name', f"Generic {category.capitalize()} in {destination}"),
                    "address": place.get('vicinity', 'N/A'),
                    "rating": place.get('rating', 4.5),
                    "distance": place.get('geometry', {}).get('location', {}).get('lat', 0)
                }
                if place.get('photos'):
                    photo_ref = place['photos'][0]['photo_reference']
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={GOOGLE_API_KEY}"
                    place_data["photo_url"] = photo_url
                else:
                    place_data["photo_url"] = None
                places.append(place_data)
            return places if places else [{"name": f"Generic {category.capitalize()} in {destination}", "address": "N/A", "rating": 4.5, "distance": 0, "photo_url": None}]
        return [{"name": f"Generic {category.capitalize()} in {destination}", "address": "N/A", "rating": 4.5, "distance": 0, "photo_url": None}]
    except Exception as e:
        logger.error(f"Google Places API error for {destination}: {str(e)}")
        return [{"name": f"Generic {category.capitalize()} in {destination}", "address": "N/A", "rating": 4.5, "distance": 0, "photo_url": None}]

# Fetch restaurants using Google Places API with photo support
def get_restaurants_google(destination, limit=3):
    coords = geocode_place(destination)
    if not coords:
        logger.error(f"Could not geocode {destination} for Restaurants API")
        return [{"name": "Local Eatery in " + destination, "cuisine": "Indian", "price_range": "₹300-500", "rating": 4.5, "address": "N/A", "photo_url": None}]

    lat, lon = coords['lat'], coords['lng']
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius=10000&type=restaurant&key={GOOGLE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Google Restaurants API response for {destination}: {data}")
        if data['status'] == 'OK':
            restaurants = []
            for place in data['results'][:limit]:
                restaurant_data = {
                    "name": "Local Eatery in " + destination,  # Generic name
                    "cuisine": "Indian",
                    "price_range": "₹300-500",
                    "rating": place.get('rating', 4.5),
                    "address": place.get('vicinity', 'N/A')
                }
                if place.get('photos'):
                    photo_ref = place['photos'][0]['photo_reference']
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={GOOGLE_API_KEY}"
                    restaurant_data["photo_url"] = photo_url
                else:
                    restaurant_data["photo_url"] = None
                restaurants.append(restaurant_data)
            return restaurants if restaurants else [{"name": "Local Eatery in " + destination, "cuisine": "Indian", "price_range": "₹300-500", "rating": 4.5, "address": "N/A", "photo_url": None}]
        return [{"name": "Local Eatery in " + destination, "cuisine": "Indian", "price_range": "₹300-500", "rating": 4.5, "address": "N/A", "photo_url": None}]
    except Exception as e:
        logger.error(f"Google Restaurants API error for {destination}: {str(e)}")
        return [{"name": "Local Eatery in " + destination, "cuisine": "Indian", "price_range": "₹300-500", "rating": 4.5, "address": "N/A", "photo_url": None}]

# Get current weather
def get_current_weather(city):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city},India"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('current'):
            weather = {
                "temperature": data['current']['temp_c'],
                "condition": data['current']['condition']['text'],
                "icon": data['current']['condition']['icon'],
                "humidity": data['current']['humidity'],
                "wind_speed": data['current']['wind_kph']
            }
            return json.dumps(weather)
        else:
            logger.error(f"No weather data for {city}")
            return json.dumps({"temperature": 25, "condition": "Clear", "icon": "", "humidity": 60, "wind_speed": 10})
    except Exception as e:
        logger.error(f"Weather API error for {city}: {e}")
        return json.dumps({"temperature": 25, "condition": "Clear", "icon": "", "humidity": 60, "wind_speed": 10})

# Get train availability via RapidAPI
def get_train_availability(start, destination, date):
    url = "https://indianrailways.p.rapidapi.com/trainsBetweenStations"
    querystring = {"fromStationCode": start.upper(), "toStationCode": destination.upper(), "date": date}
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "indianrailways.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        if data.get('trains'):
            trains = [{"number": train['number'], "name": train['name'], "departure": train['departureTime'], "arrival": train['arrivalTime'], "status": train.get('availability', 'Available')} for train in data['trains']]
            return json.dumps(trains[:1])
        else:
            logger.error(f"No train data for {start} to {destination}")
            return json.dumps([{"number": "N/A", "name": "No trains found", "departure": "N/A", "arrival": "N/A", "status": "Not available"}])
    except Exception as e:
        logger.error(f"Train API error for {start} to {destination}: {e}")
        return json.dumps([{"number": "N/A", "name": "API error", "departure": "N/A", "arrival": "N/A", "status": "Not available"}])

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"Session contents: {session}")
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to fetch tourist attractions using Google Places API
def get_places(destination):
    try:
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=tourist+attractions+in+{destination}&key={GOOGLE_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK":
            return None, f"Google Places API error: {data.get('status')}"
        places = [result["name"] for result in data.get("results", [])[:3]]
        return places, None
    except Exception as e:
        return None, f"Error fetching places: {str(e)}"

# Function to fetch current weather using OpenWeatherMap API
def get_weather(destination):
    try:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={destination}&limit=1&appid={OPENWEATHERMAP_API_KEY}"
        geo_response = requests.get(geo_url)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        if not geo_data:
            return None, "Could not find location for weather data."
        
        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        if weather_data.get("cod") != 200:
            return None, "Error fetching weather data."
        
        temp = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
        return {"temp": temp, "description": description}, None
    except Exception as e:
        return None, f"Error fetching weather: {str(e)}"

def determine_personality(answers):
    answer_key = ",".join(answers)
    return PERSONALITY_MAP.get(answer_key, PERSONALITY_MAP["default"])

def get_chatbot_response(user_message, history, session_id):
    # Initialize session if not exists
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = {
            "quiz_step": 0,
            "quiz_answers": [],
            "in_quiz": False
        }

    session_data = CHAT_SESSIONS[session_id]
    user_message = user_message.lower().strip()

    # Handle quiz initiation
    if "quiz" in user_message or "travel personality" in user_message:
        session_data["in_quiz"] = True
        session_data["quiz_step"] = 0
        session_data["quiz_answers"] = []
        return "Let’s find out your travel personality! " + TRAVEL_QUIZ[0]["question"]

    # Handle quiz answers
    if session_data["in_quiz"]:
        quiz_step = session_data["quiz_step"]
        if quiz_step < len(TRAVEL_QUIZ):
            current_question = TRAVEL_QUIZ[quiz_step]
            options = current_question["options"]
            user_answer = user_message.upper()
            if user_answer in options:
                session_data["quiz_answers"].append(options[user_answer])
                session_data["quiz_step"] += 1
                if session_data["quiz_step"] < len(TRAVEL_QUIZ):
                    return TRAVEL_QUIZ[session_data["quiz_step"]]["question"]
                else:
                    # Quiz complete, determine personality
                    personality = determine_personality(session_data["quiz_answers"])
                    session_data["in_quiz"] = False
                    suggestion = f"You’re a {personality}! "
                    if personality == "Adventure Seeker":
                        suggestion += "You’d love a thrilling trip to Munnar with trekking and waterfalls. "
                    elif personality == "Nature Explorer":
                        suggestion += "A nature-focused trip to the Western Ghats would suit you. "
                    elif personality == "Culture Explorer":
                        suggestion += "A cultural dive into Madurai’s temples and history would suit you. "
                    elif personality == "Foodie Traveler":
                        suggestion += "How about exploring Chennai’s street food scene? "
                    elif personality == "Relaxed Traveler":
                        suggestion += "A calm beach getaway in Kovalam would be perfect for you. "
                    else:
                        suggestion += "You’d enjoy a balanced trip—maybe a mix of culture and relaxation in Pondicherry. "
                    return suggestion + "Plan your detailed trip on our website’s homepage!"
            else:
                return "Please choose a valid option (A, B, C, or D). " + current_question["question"]

    # Handle trip planning redirection
    if "trip" in user_message or "itinerary" in user_message or "plan" in user_message:
        return "I can help you plan a detailed trip! Please use the Planscape Journey planner on our website to create a full itinerary. Go to the homepage and fill out the form to get started. Want a quick travel tip instead?"

    # Handle other queries with Gemini API
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        # Build conversation history
        contents = []
        for msg in history:
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["text"]}]
            })
        contents.append({
            "role": "user",
            "parts": [{
                "text": f"You are RoverBuddy, a travel assistant for Planscape Journey. Provide concise, personalized travel tips or answer specific questions. Do not generate full itineraries; instead, guide users to the website for detailed planning. Focus on local insights, packing tips, or cultural advice. User query: {user_message}"
            }]
        })

        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 100
            }
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        if "candidates" in result and result["candidates"]:
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        return "Sorry, I couldn't process your request."
    except Exception as e:
        return f"Sorry, I couldn't fetch a response: {str(e)}"
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():  # Renamed from 'about' to 'contact'
    return render_template('contact.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, start, destination, start_date FROM itineraries WHERE user_id = ?", (session['user_id'],))
    itineraries = c.fetchall()
    conn.close()
    return render_template('dashboard.html', itineraries=itineraries)

@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT transport, budget, group_size FROM preferences WHERE user_id = ?", (session['user_id'],))
    pref = c.fetchone()
    preferences = {'transport': pref[0] if pref else 'car', 'budget': pref[1] if pref else 10000, 'group_size': pref[2] if pref else 1}
    
    if request.method == 'POST':
        transport = request.form['transport'].lower()
        budget = int(request.form['budget'])
        group_size = int(request.form['group_size'])
        
        c.execute("SELECT user_id FROM preferences WHERE user_id = ?", (session['user_id'],))
        if c.fetchone():
            c.execute("UPDATE preferences SET transport = ?, budget = ?, group_size = ? WHERE user_id = ?",
                      (transport, budget, group_size, session['user_id']))
        else:
            c.execute("INSERT INTO preferences (user_id, transport, budget, group_size) VALUES (?, ?, ?, ?)",
                      (session['user_id'], transport, budget, group_size))
        conn.commit()
        flash("Preferences updated successfully!", "success")
        return redirect(url_for('dashboard'))
    
    conn.close()
    return render_template('preferences.html', preferences=preferences)


@app.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')

@app.route('/phone_auth', methods=['GET'])
@limiter.limit("5 per minute")  # Limit to 5 requests per minute per IP
def phone_auth():
    return render_template('phone_auth.html')

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')



@app.route('/success')
def success():
    if 'user_id' not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for('login'))
    action = request.args.get('action', 'signed up')
    if action == 'signup':
        action_text = 'signed up'
        next_text = 'Sign In'
        next_url = '/planner'
    else:
        action_text = 'logged in'
        next_text = 'Go to Planner'
        next_url = '/planner'
    return render_template('success.html', action=action_text, next_text=next_text, next_url=next_url)

@app.route('/forgot_password', methods=['GET'])
def forgot_password():
    logger.debug("Received GET request for /forgot_password")
    return render_template('forgot_password.html')

@app.route('/forgot_password', methods=['POST'])
def request_otp():
    logger.debug("Received POST request for /forgot_password")
    data = request.get_json()
    logger.debug(f"Request data: {data}")
    email = data.get('email')

    if not email:
        logger.debug("Email not provided in request")
        return jsonify({"status": "error", "message": "Email is required"}), 400

    try:
        # Verify if the email exists in Firebase
        user = firebase_auth.get_user_by_email(email)  # Fixed: Use firebase_auth instead of auth
        logger.debug(f"User found in Firebase: {user.uid}")
        
        # Generate OTP and set expiry (10 minutes)
        otp = generate_otp()
        expiry = datetime.now() + timedelta(minutes=10)
        otp_storage[email] = {"otp": otp, "expiry": expiry}
        logger.debug(f"Generated OTP for {email}: {otp}, expiry: {expiry}")

        # Send OTP via email
        if send_otp_email(email, otp):
            logger.debug(f"OTP sent successfully to {email}")
            return jsonify({"status": "success", "message": "OTP sent to your email"}), 200
        else:
            logger.debug("Failed to send OTP")
            return jsonify({"status": "error", "message": "Failed to send OTP"}), 500

    except firebase_auth.UserNotFoundError:
        logger.debug(f"Email not found in Firebase: {email}")
        return jsonify({"status": "error", "message": "Email not found"}), 404
    except Exception as e:
        logger.error(f"Error in request_otp: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred"}), 500

@app.route('/reset_password', methods=['GET'])
def reset_password_page():
    email = request.args.get('email')
    if not email:
        flash("Email is required to reset password", "error")
        return redirect(url_for('forgot_password'))
    return render_template('reset_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('newPassword')

    if not all([email, otp, new_password]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    # Check if OTP exists and is valid
    if email not in otp_storage:
        return jsonify({"status": "error", "message": "No OTP found for this email"}), 400

    stored_otp = otp_storage[email]
    if stored_otp['otp'] != otp:
        return jsonify({"status": "error", "message": "Invalid OTP"}), 400

    if datetime.now() > stored_otp['expiry']:
        del otp_storage[email]
        return jsonify({"status": "error", "message": "OTP has expired"}), 400

    try:
        # Update the user's password using Firebase Admin SDK
        user = firebase_auth.get_user_by_email(email)  # Fixed: Use firebase_auth instead of auth
        firebase_auth.update_user(user.uid, password=new_password)
        
        # Clear the OTP after successful reset
        del otp_storage[email]
        
        return jsonify({"status": "success", "message": "Password reset successfully"}), 200

    except Exception as e:
        logger.error(f"Error resetting password for {email}: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to reset password"}), 500

@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()
    id_token = data.get('idToken')
    if not id_token:
        return jsonify({"status": "error", "message": "ID token is required"}), 400
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        session['user_id'] = uid  # Changed from session['user'] to session['user_id']
        logger.debug(f"Session set: user_id={uid}")
        return jsonify({"status": "success", "message": "Session set successfully"}), 200
    except Exception as e:
        logger.error(f"Error verifying ID token: {str(e)}")
        return jsonify({"status": "error", "message": "Invalid ID token"}), 401
    
@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/reverse_geocode', methods=['POST'])
@login_required
def reverse_geocode_route():
    data = request.get_json()
    if not data or 'lat' not in data or 'lon' not in data:
        return jsonify({"error": "Invalid coordinates"}), 400
    
    lat = data['lat']
    lon = data['lon']
    city = reverse_geocode(lat, lon)
    
    if city:
        return jsonify({"city": city})
    else:
        return jsonify({"error": "Could not determine city"}), 500 

@app.route('/planner', methods=['GET', 'POST'])
@login_required
def planner():
    itinerary = None
    preferences = None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.args.get('edit_id'):
        c.execute("SELECT * FROM itineraries WHERE id = ? AND user_id = ?", (request.args.get('edit_id'), session['user_id']))
        itinerary_data = c.fetchone()
        if itinerary_data:
            start_coords = json.loads(itinerary_data[20]) if itinerary_data[20] else {"lat": 13.0827, "lng": 80.2707}
            dest_coords = json.loads(itinerary_data[21]) if itinerary_data[21] else {"lat": 9.9252, "lng": 78.1198}
            itinerary = {
                "id": itinerary_data[0], "start": itinerary_data[2], "destination": itinerary_data[3],
                "budget": itinerary_data[4], "days": itinerary_data[5], "group_size": itinerary_data[6],
                "transport": itinerary_data[7], "bike_model": itinerary_data[8], "transport_cost": itinerary_data[9],
                "distance": itinerary_data[10], "fuel_price": itinerary_data[11], "plan": json.loads(itinerary_data[12]),
                "total_cost": itinerary_data[13], "start_date": itinerary_data[14], "start_time": itinerary_data[15],
                "return_date": itinerary_data[14], "return_time": "18:00",  # Default for editing
                "hotel": json.loads(itinerary_data[16]) if itinerary_data[16] else None,
                "transport_details": json.loads(itinerary_data[17]) if itinerary_data[17] else None,
                "train_suggestion": itinerary_data[22] if itinerary_data[22] else "",
                "route_details": json.loads(itinerary_data[19]) if itinerary_data[19] else [{"instruction": "No route details", "distance": 0, "duration": 0}],
                "current_weather": json.loads(itinerary_data[20]) if itinerary_data[20] else None,
                "start_coords": start_coords,
                "dest_coords": dest_coords,
                "GOOGLE_API_KEY": GOOGLE_API_KEY,
                "num_vehicles": itinerary_data[23] if itinerary_data[23] is not None else 1,
                "people_per_vehicle": itinerary_data[24] if itinerary_data[24] is not None else 2,
                "intra_city_fuel_cost": itinerary_data[25] if itinerary_data[25] is not None else 0.0
            }
    c.execute("SELECT transport, budget, group_size FROM preferences WHERE user_id = ?", (session['user_id'],))
    prefs = c.fetchone()
    if prefs:
        preferences = {'transport': prefs[0], 'budget': prefs[1], 'group_size': prefs[2], 'start': 'chennai'}
    conn.close()

    if request.method == 'POST':
        start = request.form['start'].lower()
        destination = request.form['destination'].lower()
        start_coords = geocode_place(start)
        if not start_coords or not isinstance(start_coords.get('lat'), (int, float)) or not isinstance(start_coords.get('lng'), (int, float)):
            logger.error(f"Invalid start_coords for {start}: {start_coords}")
            start_coords = {"lat": 13.0827, "lng": 80.2707}  # Fallback for Chennai
        dest_coords = geocode_place(destination)
        if not dest_coords or not isinstance(dest_coords.get('lat'), (int, float)) or not isinstance(dest_coords.get('lng'), (int, float)):
            logger.error(f"Invalid dest_coords for {destination}: {dest_coords}")
            dest_coords = {"lat": 9.9252, "lng": 78.1198}  # Fallback for Madurai
        logger.debug(f"Using start_coords: {start_coords}, dest_coords: {dest_coords}")
        if not (start_coords and dest_coords):
            flash("Invalid start or destination. Please enter valid Indian locations.", "error")
            return render_template('planner.html', bike_models=bike_models, itinerary=itinerary, preferences=preferences)
        budget = int(request.form['budget'])
        group_size = int(request.form['group_size'])
        transport = request.form['transport'].lower()
        bike_model = request.form.get('bike_model', None) if transport == 'bike' else None
        fuel_price = float(request.form.get('fuel_price', FUEL_PRICE_PER_LITER))
        start_date = request.form['start_date']
        start_time = request.form['start_time']
        return_date = request.form['return_date']
        return_time = request.form['return_time']
        people_per_vehicle = int(request.form.get('people_per_vehicle', 2)) if transport in ['bike', 'car'] else group_size

        try:
            start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            return_datetime = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
            if start_datetime >= return_datetime:
                flash("Return date and time must be after start date and time!", "error")
                return render_template('planner.html', bike_models=bike_models, itinerary=itinerary, preferences=preferences)
            if start_datetime.date() < datetime.now().date():
                flash("Start date cannot be in the past!", "error")
                return render_template('planner.html', bike_models=bike_models, itinerary=itinerary, preferences=preferences)
            days = (return_datetime - start_datetime).days + 1  # Include both start and return days
        except ValueError:
            flash("Invalid date or time format!", "error")
            return render_template('planner.html', bike_models=bike_models, itinerary=itinerary, preferences=preferences)

        # Calculate number of vehicles for bike or car
        if transport in ['bike', 'car']:
            num_vehicles = (group_size + people_per_vehicle - 1) // people_per_vehicle  # Ceiling division
        else:
            num_vehicles = 1  # For bus, train, flight, assume 1 "vehicle" for simplicity

        distance, route_details = get_route_distance_google(start_coords, dest_coords)

        travel_time_hours = (distance / 70) + 1
        if transport == "flight":
            travel_time_hours = 2
        elif transport == "train":
            travel_time_hours = distance / 100
        elif transport == "bus":
            travel_time_hours = distance / 60
        elif transport == "car":
            travel_time_hours = (distance / 50) + 1
        start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        return_dt = datetime.strptime(f"{return_date} {return_time}", "%Y-%m-%d %H:%M")
        arrival_dt = start_dt + timedelta(hours=travel_time_hours)

        transport_cost = 0
        train_suggestion = ""
        if transport == 'bike' and bike_model:
            mileage = bike_models[bike_model]['mileage']
            fuel_needed = distance / mileage
            transport_cost = fuel_needed * fuel_price * num_vehicles
        elif transport == 'bus':
            transport_cost = distance * 1.5 * group_size
        elif transport == 'train':
            transport_cost = distance * 2 * group_size
            date_str = start_date
            train_data = get_train_availability(start.upper(), destination.upper(), date_str)
            trains = json.loads(train_data)
            if trains and trains[0]['number'] != "N/A":
                train_suggestion = f"Suggested Train: {trains[0]['name']} (No. {trains[0]['number']}), Dep: {trains[0]['departure']}, Arr: {trains[0]['arrival']}, Status: {trains[0]['status']}"
        elif transport == 'flight':
            transport_cost = distance * 5 * group_size
        elif transport == 'car':
            fuel_needed = distance / 15  # Average car mileage of 15 km/liter
            transport_cost = fuel_needed * fuel_price * num_vehicles

        # Fetch places (focus on tourist attractions, hill stations, and beaches)
        attractions = get_places_google(destination, "tourist_attraction", 5)
        hill_stations = get_places_google(destination, "hill_station", 3)
        beaches = get_places_google(destination, "beach", 3)
        hidden_gems = get_places_google(destination, "hidden_gem", 3)
        hotels = get_places_google(destination, "lodging", 1)
        restaurants = get_restaurants_google(destination, 5)
        current_weather = get_current_weather(destination)

        hotel = hotels[0] if hotels else {"name": "Local Hotel", "address": "N/A", "rating": 4.0, "photo_url": None}
        # Adjust hotel cost based on budget
        hotel_cost_per_night = 1000 * group_size  # Base cost
        if budget < 5000:
            hotel_cost_per_night = 500 * group_size  # Budget hotel
        elif budget < 10000:
            hotel_cost_per_night = 800 * group_size  # Mid-range hotel
        hotel_cost = hotel_cost_per_night * days

        # Estimate intra-city travel distances (simplified as a fixed distance per activity)
        intra_city_distance_per_activity = 5  # Assume 5 km per activity within the city
        num_activities_per_day = 3  # Approximate number of places visited per day (excluding meals)
        intra_city_distance_daily = intra_city_distance_per_activity * num_activities_per_day
        intra_city_fuel_cost = 0
        if transport == 'bike' and bike_model:
            mileage = bike_models[bike_model]['mileage']
            fuel_needed_daily = intra_city_distance_daily / mileage
            intra_city_fuel_cost = fuel_needed_daily * fuel_price * num_vehicles * days
        elif transport == 'car':
            fuel_needed_daily = intra_city_distance_daily / 15
            intra_city_fuel_cost = fuel_needed_daily * fuel_price * num_vehicles * days

        # Adjust activity costs based on budget
        base_activity_cost = 100 * group_size  # Default cost per activity
        base_meal_cost = 200 * group_size  # Default cost per meal
        if budget < 5000:
            base_activity_cost = 50 * group_size
            base_meal_cost = 100 * group_size
        elif budget < 10000:
            base_activity_cost = 75 * group_size
            base_meal_cost = 150 * group_size

        # Generate the itinerary plan
        plan = []
        total_cost = transport_cost + intra_city_fuel_cost + hotel_cost
        current_time = start_dt
        visited_places = set()
        daily_activity_count = 0
        max_activities_per_day = 4  # Including meals
        max_meals_per_day = 2

        for day in range(days):
            day_plan = {"day": day + 1, "schedule": []}
            day_date = (start_dt + timedelta(days=day)).strftime("%Y-%m-%d")
            day_plan["date"] = day_date
            daily_end_time = datetime.strptime(f"{day_date} 22:00", "%Y-%m-%d %H:%M")  # Stop activities by 10:00 PM
            daily_activity_count = 0
            daily_meal_count = 0

            if day == 0:
                # Day 1: Travel to destination and initial activities
                travel_end = current_time + timedelta(hours=travel_time_hours)
                if travel_end > daily_end_time:
                    travel_end = daily_end_time
                day_plan["schedule"].append({
                    "time": f"{current_time.strftime('%H:%M')} - {travel_end.strftime('%H:%M')}",
                    "activity": f"Travel to {destination.capitalize()}",
                    "cost": transport_cost,
                    "place_name": destination.capitalize(),
                    "place_type": "transport",
                    "photo_url": None
                })
                current_time = travel_end + timedelta(minutes=30)
                daily_activity_count += 1

                # Lunch on Day 1 if time allows
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and current_time < daily_end_time:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"Enjoy a {selected_rest.get('cuisine', 'Indian')} meal in a welcoming atmosphere, perfect for a break during your travels.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Lunch",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

                # Add a tourist attraction if budget allows
                if attractions and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                    available_attractions = [attr for attr in attractions if attr['name'] not in visited_places]
                    if available_attractions:
                        selected_attr = random.choice(available_attractions)
                        attr_details = get_place_details(selected_attr['name'])
                        visited_places.add(selected_attr['name'])
                        activity_end = current_time + timedelta(hours=3)  # More time for attractions
                        if activity_end > daily_end_time:
                            activity_end = daily_end_time
                        why_famous = attr_details.get('why_famous', attr_details.get('editorial_summary', f"A popular landmark in {destination.capitalize()} known for its historical or cultural significance."))
                        why_visit = attr_details.get('why_visit', f"Explore this iconic site to learn about the history and culture of {destination.capitalize()}.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                            "activity": f"Visit {selected_attr['name']}",
                            "cost": base_activity_cost,
                            "place_name": selected_attr['name'],
                            "place_type": "tourist_attraction",
                            "rating": selected_attr.get('rating', attr_details.get('rating')),
                            "photo_url": selected_attr.get('photo_url', attr_details.get('photo_url')),
                            "old_things_review": attr_details.get('old_things_review', f"This attraction has been a highlight in {destination.capitalize()} for decades."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": attr_details.get('special_occasion', "Best visited during local festivals for a vibrant experience."),
                            "safety": attr_details.get('safety', "Generally safe, but be cautious of crowds during peak times."),
                            "maps_link": attr_details.get('maps_link'),
                            "youtube_link": attr_details.get('youtube_link'),
                            "reviews": attr_details.get('reviews', [])
                        })
                        total_cost += base_activity_cost
                        current_time = activity_end + timedelta(minutes=30)
                        daily_activity_count += 1

                # Add a hidden gem if budget allows
                if hidden_gems and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                    available_gems = [gem for gem in hidden_gems if gem['name'] not in visited_places]
                    if available_gems:
                        selected_gem = random.choice(available_gems)
                        gem_details = get_place_details(selected_gem['name'])
                        visited_places.add(selected_gem['name'])
                        hidden_end = current_time + timedelta(hours=3)  # More time for exploration
                        if hidden_end > daily_end_time:
                            hidden_end = daily_end_time
                        why_famous = gem_details.get('why_famous', gem_details.get('editorial_summary', f"A lesser-known spot in {destination.capitalize()} cherished by locals for its unique charm."))
                        why_visit = gem_details.get('why_visit', f"Discover a quiet retreat away from the usual tourist spots in {destination.capitalize()}.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {hidden_end.strftime('%H:%M')}",
                            "activity": f"Explore Hidden Gem: {selected_gem['name']}",
                            "cost": base_activity_cost,
                            "place_name": selected_gem['name'],
                            "place_type": "hidden_gem",
                            "rating": selected_gem.get('rating', gem_details.get('rating')),
                            "photo_url": selected_gem.get('photo_url', gem_details.get('photo_url')),
                            "old_things_review": gem_details.get('old_things_review', f"A lesser-known spot in {destination.capitalize()}, cherished by locals for decades."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": gem_details.get('special_occasion', "Ideal for a quiet visit during weekdays to avoid small crowds."),
                            "safety": gem_details.get('safety', "Safe for visitors, though it’s best to visit during daylight hours."),
                            "maps_link": gem_details.get('maps_link'),
                            "youtube_link": gem_details.get('youtube_link'),
                            "reviews": gem_details.get('reviews', [])
                        })
                        total_cost += base_activity_cost
                        current_time = hidden_end + timedelta(minutes=30)
                        daily_activity_count += 1

                # Dinner on Day 1 if time allows
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time and current_time.hour < 20:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"End your day with a delicious {selected_rest.get('cuisine', 'Indian')} dinner in a cozy setting.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Dinner",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

            elif day < days - 1:
                # Intermediate days: Full day of activities
                current_time = datetime.strptime(f"{day_date} 07:00", "%Y-%m-%d %H:%M")
                daily_activity_count = 0
                daily_meal_count = 0

                # Breakfast
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"Start your day with a hearty {selected_rest.get('cuisine', 'Indian')} breakfast in a welcoming setting.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Breakfast",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

                # Visit a hill station if available and budget allows
                if hill_stations and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                    available_hills = [hill for hill in hill_stations if hill['name'] not in visited_places]
                    if available_hills:
                        selected_hill = random.choice(available_hills)
                        hill_details = get_place_details(selected_hill['name'])
                        visited_places.add(selected_hill['name'])
                        activity_end = current_time + timedelta(hours=3)
                        if activity_end > daily_end_time:
                            activity_end = daily_end_time
                        why_famous = hill_details.get('why_famous', hill_details.get('editorial_summary', f"Known for its scenic views and cool climate near {destination.capitalize()}."))
                        why_visit = hill_details.get('why_visit', f"Enjoy a refreshing escape with stunning views and outdoor activities near {destination.capitalize()}.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                            "activity": f"Visit {selected_hill['name']}",
                            "cost": base_activity_cost,
                            "place_name": selected_hill['name'],
                            "place_type": "hill_station",
                            "rating": selected_hill.get('rating', hill_details.get('rating')),
                            "photo_url": selected_hill.get('photo_url', hill_details.get('photo_url')),
                            "old_things_review": hill_details.get('old_things_review', f"This hill station has been a popular retreat near {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": hill_details.get('special_occasion', "Best visited during summer for a cool retreat or winter for misty views."),
                            "safety": hill_details.get('safety', "Safe, but be cautious on hilly roads and during monsoon seasons."),
                            "maps_link": hill_details.get('maps_link'),
                            "youtube_link": hill_details.get('youtube_link'),
                            "reviews": hill_details.get('reviews', [])
                        })
                        total_cost += base_activity_cost
                        current_time = activity_end + timedelta(minutes=30)
                        daily_activity_count += 1

                # Visit a beach if available and budget allows
                if beaches and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                    available_beaches = [beach for beach in beaches if beach['name'] not in visited_places]
                    if available_beaches:
                        selected_beach = random.choice(available_beaches)
                        beach_details = get_place_details(selected_beach['name'])
                        visited_places.add(selected_beach['name'])
                        activity_end = current_time + timedelta(hours=3)
                        if activity_end > daily_end_time:
                            activity_end = daily_end_time
                        why_famous = beach_details.get('why_famous', beach_details.get('editorial_summary', f"Known for its scenic shoreline near {destination.capitalize()}."))
                        why_visit = beach_details.get('why_visit', f"Relax on the beach and enjoy water activities near {destination.capitalize()}.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                            "activity": f"Visit {selected_beach['name']}",
                            "cost": base_activity_cost,
                            "place_name": selected_beach['name'],
                            "place_type": "beach",
                            "rating": selected_beach.get('rating', beach_details.get('rating')),
                            "photo_url": selected_beach.get('photo_url', beach_details.get('photo_url')),
                            "old_things_review": beach_details.get('old_things_review', f"This beach has been a beloved spot near {destination.capitalize()} for decades."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": beach_details.get('special_occasion', "Perfect for beach festivals or during early mornings for serene views."),
                            "safety": beach_details.get('safety', "Safe for swimming in designated areas; follow lifeguard instructions."),
                            "maps_link": beach_details.get('maps_link'),
                            "youtube_link": beach_details.get('youtube_link'),
                            "reviews": beach_details.get('reviews', [])
                        })
                        total_cost += base_activity_cost
                        current_time = activity_end + timedelta(minutes=30)
                        daily_activity_count += 1

                # Lunch
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time and current_time.hour < 15:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"Enjoy a {selected_rest.get('cuisine', 'Indian')} lunch in a welcoming setting during your travels.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Lunch",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

                # Add another tourist attraction if budget allows
                if attractions and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                    available_attractions = [attr for attr in attractions if attr['name'] not in visited_places]
                    if available_attractions:
                        selected_attr = random.choice(available_attractions)
                        attr_details = get_place_details(selected_attr['name'])
                        visited_places.add(selected_attr['name'])
                        activity_end = current_time + timedelta(hours=3)
                        if activity_end > daily_end_time:
                            activity_end = daily_end_time
                        why_famous = attr_details.get('why_famous', attr_details.get('editorial_summary', f"A popular landmark in {destination.capitalize()} known for its historical or cultural significance."))
                        why_visit = attr_details.get('why_visit', f"Explore this iconic site to learn about the history and culture of {destination.capitalize()}.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                            "activity": f"Visit {selected_attr['name']}",
                            "cost": base_activity_cost,
                            "place_name": selected_attr['name'],
                            "place_type": "tourist_attraction",
                            "rating": selected_attr.get('rating', attr_details.get('rating')),
                            "photo_url": selected_attr.get('photo_url', attr_details.get('photo_url')),
                            "old_things_review": attr_details.get('old_things_review', f"This attraction has been a highlight in {destination.capitalize()} for decades."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": attr_details.get('special_occasion', "Best visited during local festivals for a vibrant experience."),
                            "safety": attr_details.get('safety', "Generally safe, but be cautious of crowds during peak times."),
                            "maps_link": attr_details.get('maps_link'),
                            "youtube_link": attr_details.get('youtube_link'),
                            "reviews": attr_details.get('reviews', [])
                        })
                        total_cost += base_activity_cost
                        current_time = activity_end + timedelta(minutes=30)
                        daily_activity_count += 1

                # Dinner
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time and current_time.hour < 20:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"End your day with a delicious {selected_rest.get('cuisine', 'Indian')} dinner in a cozy setting.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Dinner",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

            else:
                # Last day: Activities until return
                current_time = datetime.strptime(f"{day_date} 07:00", "%Y-%m-%d %H:%M")
                daily_activity_count = 0
                daily_meal_count = 0

                # Breakfast
                if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time:
                    available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                    if available_rest:
                        selected_rest = random.choice(available_rest)
                        visited_places.add(selected_rest['name'])
                        meal_end = current_time + timedelta(hours=1.5)
                        if meal_end > daily_end_time:
                            meal_end = daily_end_time
                        if meal_end > return_dt:
                            meal_end = return_dt
                        restaurant_details = get_place_details(selected_rest['name'])
                        why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                        why_visit = restaurant_details.get('why_visit', f"Start your day with a hearty {selected_rest.get('cuisine', 'Indian')} breakfast in a welcoming setting.")
                        day_plan["schedule"].append({
                            "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                            "activity": "Breakfast",
                            "cost": base_meal_cost,
                            "place_name": selected_rest['name'],
                            "place_type": "restaurant",
                            "cuisine": selected_rest.get('cuisine', "Indian"),
                            "price_range": restaurant_details.get('price_range', "₹300-500"),
                            "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                            "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                            "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                            "why_famous": why_famous,
                            "why_visit": why_visit,
                            "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                            "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                            "maps_link": restaurant_details.get('maps_link'),
                            "youtube_link": restaurant_details.get('youtube_link')
                        })
                        total_cost += base_meal_cost
                        current_time = meal_end + timedelta(minutes=30)
                        daily_activity_count += 1
                        daily_meal_count += 1

                while current_time < return_dt and current_time < daily_end_time and daily_activity_count < max_activities_per_day:
                    time_until_return = (return_dt - current_time).total_seconds() / 3600
                    if time_until_return < 1:
                        break

                    # Visit a hill station if available and budget allows
                    if hill_stations and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                        available_hills = [hill for hill in hill_stations if hill['name'] not in visited_places]
                        if available_hills:
                            selected_hill = random.choice(available_hills)
                            hill_details = get_place_details(selected_hill['name'])
                            visited_places.add(selected_hill['name'])
                            activity_duration = min(3, time_until_return)
                            activity_end = current_time + timedelta(hours=activity_duration)
                            if activity_end > daily_end_time:
                                activity_end = daily_end_time
                            if activity_end > return_dt:
                                activity_end = return_dt
                            why_famous = hill_details.get('why_famous', hill_details.get('editorial_summary', f"Known for its scenic views and cool climate near {destination.capitalize()}."))
                            why_visit = hill_details.get('why_visit', f"Enjoy a refreshing escape with stunning views and outdoor activities near {destination.capitalize()}.")
                            day_plan["schedule"].append({
                                "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                                "activity": f"Visit {selected_hill['name']}",
                                "cost": base_activity_cost,
                                "place_name": selected_hill['name'],
                                "place_type": "hill_station",
                                "rating": selected_hill.get('rating', hill_details.get('rating')),
                                "photo_url": selected_hill.get('photo_url', hill_details.get('photo_url')),
                                "old_things_review": hill_details.get('old_things_review', f"This hill station has been a popular retreat near {destination.capitalize()} for years."),
                                "why_famous": why_famous,
                                "why_visit": why_visit,
                                "special_occasion": hill_details.get('special_occasion', "Best visited during summer for a cool retreat or winter for misty views."),
                                "safety": hill_details.get('safety', "Safe, but be cautious on hilly roads and during monsoon seasons."),
                                "maps_link": hill_details.get('maps_link'),
                                "youtube_link": hill_details.get('youtube_link'),
                                "reviews": hill_details.get('reviews', [])
                            })
                            total_cost += base_activity_cost
                            current_time = activity_end + timedelta(minutes=30)
                            daily_activity_count += 1
                            continue

                    # Visit a beach if available and budget allows
                    if beaches and daily_activity_count < max_activities_per_day and total_cost + base_activity_cost <= budget and current_time < daily_end_time:
                        available_beaches = [beach for beach in beaches if beach['name'] not in visited_places]
                        if available_beaches:
                            selected_beach = random.choice(available_beaches)
                            beach_details = get_place_details(selected_beach['name'])
                            visited_places.add(selected_beach['name'])
                            activity_duration = min(3, time_until_return)
                            activity_end = current_time + timedelta(hours=activity_duration)
                            if activity_end > daily_end_time:
                                activity_end = daily_end_time
                            if activity_end > return_dt:
                                activity_end = return_dt
                            why_famous = beach_details.get('why_famous', beach_details.get('editorial_summary', f"Known for its scenic shoreline near {destination.capitalize()}."))
                            why_visit = beach_details.get('why_visit', f"Relax on the beach and enjoy water activities near {destination.capitalize()}.")
                            day_plan["schedule"].append({
                                "time": f"{current_time.strftime('%H:%M')} - {activity_end.strftime('%H:%M')}",
                                "activity": f"Visit {selected_beach['name']}",
                                "cost": base_activity_cost,
                                "place_name": selected_beach['name'],
                                "place_type": "beach",
                                "rating": selected_beach.get('rating', beach_details.get('rating')),
                                "photo_url": selected_beach.get('photo_url', beach_details.get('photo_url')),
                                "old_things_review": beach_details.get('old_things_review', f"This beach has been a beloved spot near {destination.capitalize()} for decades."),
                                "why_famous": why_famous,
                                "why_visit": why_visit,
                                "special_occasion": beach_details.get('special_occasion', "Perfect for beach festivals or during early mornings for serene views."),
                                "safety": beach_details.get('safety', "Safe for swimming in designated areas; follow lifeguard instructions."),
                                "maps_link": beach_details.get('maps_link'),
                                "youtube_link": beach_details.get('youtube_link'),
                                "reviews": beach_details.get('reviews', [])
                            })
                            total_cost += base_activity_cost
                            current_time = activity_end + timedelta(minutes=30)
                            daily_activity_count += 1
                            continue

                    # Lunch on last day if time allows
                    if restaurants and daily_activity_count < max_activities_per_day and daily_meal_count < max_meals_per_day and total_cost + base_meal_cost <= budget and current_time < daily_end_time and current_time.hour < 15:
                        available_rest = [rest for rest in restaurants if rest['name'] not in visited_places]
                        if available_rest:
                            selected_rest = random.choice(available_rest)
                            visited_places.add(selected_rest['name'])
                            meal_duration = min(1.5, time_until_return)
                            meal_end = current_time + timedelta(hours=meal_duration)
                            if meal_end > daily_end_time:
                                meal_end = daily_end_time
                            if meal_end > return_dt:
                                meal_end = return_dt
                            restaurant_details = get_place_details(selected_rest['name'])
                            why_famous = restaurant_details.get('why_famous', restaurant_details.get('editorial_summary', f"Known for its {selected_rest.get('cuisine', 'Indian')} cuisine in {destination.capitalize()}."))
                            why_visit = restaurant_details.get('why_visit', f"Enjoy a {selected_rest.get('cuisine', 'Indian')} lunch in a welcoming setting during your travels.")
                            day_plan["schedule"].append({
                                "time": f"{current_time.strftime('%H:%M')} - {meal_end.strftime('%H:%M')}",
                                "activity": "Lunch",
                                "cost": base_meal_cost,
                                "place_name": selected_rest['name'],
                                "place_type": "restaurant",
                                "cuisine": selected_rest.get('cuisine', "Indian"),
                                "price_range": restaurant_details.get('price_range', "₹300-500"),
                                "rating": selected_rest.get('rating', restaurant_details.get('rating')),
                                "photo_url": selected_rest.get('photo_url', restaurant_details.get('photo_url')),
                                "old_things_review": restaurant_details.get('old_things_review', f"This restaurant has been a popular spot in {destination.capitalize()} for years."),
                                "why_famous": why_famous,
                                "why_visit": why_visit,
                                "special_occasion": restaurant_details.get('special_occasion', "Great for festive seasons or local events."),
                                "safety": restaurant_details.get('safety', "Safe and family-friendly; may be busy during peak hours."),
                                "maps_link": restaurant_details.get('maps_link'),
                                "youtube_link": restaurant_details.get('youtube_link')
                            })
                            total_cost += base_meal_cost
                            current_time = meal_end + timedelta(minutes=30)
                            daily_activity_count += 1
                            daily_meal_count += 1
                            continue

                    break

                # Return journey
                return_start = return_dt - timedelta(hours=travel_time_hours)
                if return_start < current_time:
                    return_start = current_time
                return_end = return_start + timedelta(hours=travel_time_hours)
                if return_end > daily_end_time:
                    return_end = daily_end_time
                    return_start = return_end - timedelta(hours=travel_time_hours)
                day_plan["schedule"].append({
                    "time": f"{return_start.strftime('%H:%M')} - {return_end.strftime('%H:%M')}",
                    "activity": "Return to Start",
                    "cost": 0,
                    "place_name": start.capitalize(),
                    "place_type": "transport",
                    "photo_url": None
                })

            # Add hotel stay at the end of each day (night only, no morning stay)
            if current_time < daily_end_time and day < days - 1:  # No hotel stay on the last day
                hotel_start = max(current_time, daily_end_time)
                hotel_end = datetime.strptime(f"{day_date} 23:59", "%Y-%m-%d %H:%M")
                hotel_details = get_place_details(hotel['name'])
                why_famous = hotel_details.get('why_famous', hotel_details.get('editorial_summary', f"Known for its comfortable rooms and proximity to local attractions in {destination.capitalize()}."))
                why_visit = hotel_details.get('why_visit', f"A great place to unwind after a long journey, offering modern amenities and a welcoming atmosphere.")
                day_plan["schedule"].append({
                    "time": f"{hotel_start.strftime('%H:%M')} - 07:00 (next day)",
                    "activity": "Hotel Stay (Night)",
                    "cost": 0,  # Already included in total hotel cost
                    "place_name": hotel['name'],
                    "place_type": "hotel",
                    "rating": hotel.get('rating', hotel_details.get('rating')),
                    "photo_url": hotel.get('photo_url', hotel_details.get('photo_url')),
                    "old_things_review": hotel_details.get('old_things_review', f"Established in the early 2000s, this hotel has been a staple for travelers in {destination.capitalize()}."),
                    "why_famous": why_famous,
                    "why_visit": why_visit,
                    "special_occasion": hotel_details.get('special_occasion', "Popular during local festivals or peak tourist seasons for its accessibility."),
                    "safety": hotel_details.get('safety', "Safe with 24/7 staff support; located in a secure area, though caution is advised at night."),
                    "maps_link": hotel_details.get('maps_link'),
                    "youtube_link": hotel_details.get('youtube_link')
                })

            plan.append(day_plan)

        itinerary = {
            "start": start, "destination": destination, "budget": budget, "days": days,
            "group_size": group_size, "transport": transport, "bike_model": bike_model,
            "transport_cost": transport_cost, "distance": distance, "fuel_price": fuel_price, "plan": plan,
            "total_cost": total_cost, "start_date": start_date, "start_time": start_time, "return_date": return_date, "return_time": return_time,
            "hotel": hotel,
            "route_details": json.loads(route_details),
            "current_weather": json.loads(current_weather),
            "start_coords": start_coords,
            "dest_coords": dest_coords,
            "train_suggestion": train_suggestion,
            "GOOGLE_API_KEY": GOOGLE_API_KEY,
            "num_vehicles": num_vehicles,
            "people_per_vehicle": people_per_vehicle,
            "intra_city_fuel_cost": intra_city_fuel_cost
        }
 
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO itineraries (user_id, start, destination, budget, days, group_size, transport, bike_model, transport_cost, distance, fuel_price, plan, total_cost, start_date, start_time, hotel, route_details, current_weather, start_coords, dest_coords, train_suggestion, num_vehicles, people_per_vehicle, intra_city_fuel_cost)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (session['user_id'], start, destination, budget, days, group_size, transport, bike_model,
                   transport_cost, distance, fuel_price, json.dumps(plan), total_cost, start_date, start_time, json.dumps(hotel), route_details, current_weather, json.dumps(start_coords), json.dumps(dest_coords), train_suggestion, num_vehicles, people_per_vehicle, intra_city_fuel_cost))
        conn.commit()
        itinerary_id = c.lastrowid
        conn.close()

        return redirect(url_for('view_itinerary', itinerary_id=itinerary_id))
    return render_template('planner.html', bike_models=bike_models, itinerary=itinerary, preferences=preferences)

@app.route('/itinerary/<int:itinerary_id>')
@login_required
def view_itinerary(itinerary_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM itineraries WHERE id = ? AND user_id = ?", (itinerary_id, session['user_id']))
    itinerary_data = c.fetchone()
    conn.close()
    
    if not itinerary_data:
        flash("Itinerary not found!", "error")
        return redirect(url_for('dashboard'))

    start_coords = json.loads(itinerary_data[20]) if itinerary_data[20] else {"lat": 13.0827, "lng": 80.2707}
    dest_coords = json.loads(itinerary_data[21]) if itinerary_data[21] else {"lat": 9.9252, "lng": 78.1198}
    
    try:
        num_vehicles = int(itinerary_data[23]) if itinerary_data[23] is not None else 1
    except (ValueError, TypeError):
        num_vehicles = 1
    try:
        people_per_vehicle = int(itinerary_data[24]) if itinerary_data[24] is not None else 2
    except (ValueError, TypeError):
        people_per_vehicle = 2
    
    itinerary_dict = {
        "id": itinerary_data[0],
        "start": itinerary_data[2],
        "destination": itinerary_data[3],
        "budget": float(itinerary_data[4]) if itinerary_data[4] is not None else 0.0,
        "days": int(itinerary_data[5]) if itinerary_data[5] is not None else 1,
        "group_size": int(itinerary_data[6]) if itinerary_data[6] is not None else 1,
        "transport": itinerary_data[7],
        "bike_model": itinerary_data[8],
        "transport_cost": float(itinerary_data[9]) if itinerary_data[9] is not None else 0.0,
        "distance": float(itinerary_data[10]) if itinerary_data[10] is not None else 0.0,
        "fuel_price": float(itinerary_data[11]) if itinerary_data[11] is not None else 0.0,
        "plan": json.loads(itinerary_data[12]) if itinerary_data[12] else [],
        "total_cost": float(itinerary_data[13]) if itinerary_data[13] is not None else 0.0,
        "start_date": itinerary_data[14],
        "start_time": itinerary_data[15],
        "return_date": itinerary_data[14],
        "return_time": "18:00",  # Default for display
        "hotel": json.loads(itinerary_data[16]) if itinerary_data[16] else None,
        "route_details": json.loads(itinerary_data[17]) if itinerary_data[17] else [{"instruction": "No route details", "distance": 0, "duration": 0}],
        "current_weather": json.loads(itinerary_data[19]) if itinerary_data[19] else None,
        "start_coords": start_coords,
        "dest_coords": dest_coords,
        "train_suggestion": itinerary_data[22] if itinerary_data[22] else "",
        "num_vehicles": num_vehicles,
        "people_per_vehicle": people_per_vehicle,
        "intra_city_fuel_cost": float(itinerary_data[25]) if itinerary_data[25] is not None else 0.0,
        "tour_mode": itinerary_data[26] if itinerary_data[26] is not None else "relaxation"
    }
    return render_template('itinerary.html', itinerary=itinerary_dict, GOOGLE_API_KEY=GOOGLE_API_KEY)

@app.route('/delete_itinerary/<int:itinerary_id>', methods=['POST'])
@login_required
def delete_itinerary(itinerary_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM itineraries WHERE id = ? AND user_id = ?", (itinerary_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Itinerary deleted successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/download_itinerary', methods=['POST'])
@login_required
def download_itinerary():
    # Log the raw form data to debug
    itinerary = request.form.to_dict()
    logger.debug(f"Received form data: {itinerary}")

    # Check for required keys
    required_keys = ['plan', 'hotel', 'budget', 'days', 'group_size', 'transport_cost', 
                     'distance', 'fuel_price', 'total_cost', 'route_details', 
                     'current_weather', 'start', 'destination', 'start_date', 
                     'start_time', 'return_date', 'return_time', 'train_suggestion']
    missing_keys = [key for key in required_keys if key not in itinerary]
    if missing_keys:
        logger.error(f"Missing required keys in form data: {missing_keys}")
        flash(f"Missing required data: {', '.join(missing_keys)}. Please try again.", "error")
        return redirect(url_for('planner'))

    try:
        # Parse JSON fields
        try:
            itinerary['plan'] = json.loads(itinerary['plan'])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 'plan' as JSON: {itinerary['plan']}, Error: {e}")
            raise ValueError("Invalid 'plan' data format")

        try:
            itinerary['hotel'] = json.loads(itinerary['hotel']) if itinerary['hotel'] else {"name": "Local Hotel", "address": "N/A", "rating": 4.0, "photo_url": None}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 'hotel' as JSON: {itinerary['hotel']}, Error: {e}")
            raise ValueError("Invalid 'hotel' data format")

        try:
            itinerary['route_details'] = json.loads(itinerary['route_details']) if itinerary['route_details'] else [{"instruction": "No route details", "distance": 0, "duration": 0}]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 'route_details' as JSON: {itinerary['route_details']}, Error: {e}")
            raise ValueError("Invalid 'route_details' data format")

        try:
            itinerary['current_weather'] = json.loads(itinerary['current_weather']) if itinerary['current_weather'] else {"temperature": 25, "condition": "Clear", "icon": "", "humidity": 60, "wind_speed": 10}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse 'current_weather' as JSON: {itinerary['current_weather']}, Error: {e}")
            raise ValueError("Invalid 'current_weather' data format")

        # Convert numeric fields
        try:
            itinerary['budget'] = float(itinerary['budget'])
        except ValueError as e:
            logger.error(f"Failed to convert 'budget' to float: {itinerary['budget']}, Error: {e}")
            raise ValueError("Invalid 'budget' value")

        try:
            itinerary['days'] = int(itinerary['days'])
        except ValueError as e:
            logger.error(f"Failed to convert 'days' to int: {itinerary['days']}, Error: {e}")
            raise ValueError("Invalid 'days' value")

        try:
            itinerary['group_size'] = int(itinerary['group_size'])
        except ValueError as e:
            logger.error(f"Failed to convert 'group_size' to int: {itinerary['group_size']}, Error: {e}")
            raise ValueError("Invalid 'group_size' value")

        try:
            itinerary['transport_cost'] = float(itinerary['transport_cost'])
        except ValueError as e:
            logger.error(f"Failed to convert 'transport_cost' to float: {itinerary['transport_cost']}, Error: {e}")
            raise ValueError("Invalid 'transport_cost' value")

        try:
            itinerary['distance'] = float(itinerary['distance'])
        except ValueError as e:
            logger.error(f"Failed to convert 'distance' to float: {itinerary['distance']}, Error: {e}")
            raise ValueError("Invalid 'distance' value")

        try:
            itinerary['fuel_price'] = float(itinerary['fuel_price'])
        except ValueError as e:
            logger.error(f"Failed to convert 'fuel_price' to float: {itinerary['fuel_price']}, Error: {e}")
            raise ValueError("Invalid 'fuel_price' value")

        try:
            itinerary['total_cost'] = float(itinerary['total_cost'])
        except ValueError as e:
            logger.error(f"Failed to convert 'total_cost' to float: {itinerary['total_cost']}, Error: {e}")
            raise ValueError("Invalid 'total_cost' value")

    except (ValueError, KeyError) as e:
        logger.error(f"Error processing itinerary data: {e}")
        flash(f"Invalid itinerary data: {str(e)}. Please try again.", "error")
        return redirect(url_for('planner'))

    # Building the LaTeX content
    latex_content = r"""
% Defining document class and essential packages
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{margin=1in}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{datetime}

% Setting up fonts and styling
\usepackage{times}

% Customizing section titles
\titleformat{\section}{\large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{1em}{}

% Defining custom commands for consistent formatting
\newcommand{\itinerarytitle}[1]{\section*{#1}}
\newcommand{\tripinfo}[2]{\textbf{#1:} #2 \\}
\newcommand{\dayplan}[1]{\subsection*{Day #1 -- \today}}
\newcommand{\activity}[3]{\item \textbf{#1 -- #2:} #3}

\begin{document}

% Adding title for the itinerary
\itinerarytitle{Planscape Itinerary}
\vspace{10pt}

% Including trip summary information
\begin{itemize}[leftmargin=*]
    \tripinfo{Trip}{""" + f"{itinerary['start'].capitalize()} to {itinerary['destination'].capitalize()} ({itinerary['distance']} km)" + r"""}
    \tripinfo{Total Days}{""" + f"{itinerary['days']}" + r"""}
    \tripinfo{Start}{""" + f"{itinerary['start_date']} at {itinerary['start_time']}" + r"""}
    \tripinfo{Return}{""" + f"{itinerary['return_date']} at {itinerary['return_time']}" + r"""}
    \tripinfo{Hotel}{""" + f"{itinerary['hotel']['name']}" + r"""}
    \tripinfo{Budget}{\rupee """ + f"{itinerary['budget']}" + r""" | Total Cost: \rupee """ + f"{itinerary['total_cost']}" + r"""}
    \tripinfo{Current Weather}{""" + f"{itinerary['current_weather']['condition']}, {itinerary['current_weather']['temperature']}$^\circ$C" + r"""}
    \tripinfo{Train Suggestion}{""" + f"{itinerary['train_suggestion']}" + r"""}
\end{itemize}

% Adding route details
\section*{Route Details}
\begin{itemize}[leftmargin=*]
"""

    # Add route details
    for step in itinerary['route_details']:
        instruction = step['instruction'].replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
        latex_content += f"    \\item {instruction} (Distance: {step['distance']} km, Duration: {step['duration']} mins)\n"

    latex_content += r"""
\end{itemize}

% Adding daily itinerary plans
\section*{Daily Itinerary}
"""

    # Add daily plans
    for day in itinerary['plan']:
        latex_content += f"    \\dayplan{{{day['day']}}}\n"
        latex_content += r"    \begin{itemize}[leftmargin=*]" + "\n"
        for activity in day['schedule']:
            activity_name = activity['activity'].replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
            place_name = activity['place_name'].replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
            latex_content += f"        \\activity{{{activity['time']}}}{{{place_name}}}{{{activity_name}}} (Cost: \\rupee{{{activity['cost']}}})\n"
        latex_content += r"    \end{itemize}" + "\n"

    latex_content += r"""
\end{document}
"""

    # Return the LaTeX content as a response
    response = app.response_class(
        response=latex_content,
        mimetype='application/x-latex',
        headers={'Content-Disposition': 'attachment;filename=Planscape_Itinerary.tex'}
    )
    return response

@app.route('/map')
@login_required
def map_page():
    return render_template('map.html')

# Route to render the chat page
@app.route('/chat')
def chat_page():
    # Generate a unique session ID (in a real app, tie this to user session)
    session_id = str(random.randint(1000, 9999))
    return render_template('chat.html', session_id=session_id)

# API endpoint to handle chat messages
@app.route('/chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '')
    history = data.get('history', [])
    session_id = data.get('session_id', 'default')
    if not user_message:
        return jsonify({'response': 'Please send a message!'}), 400
    
    response = get_chatbot_response(user_message, history, session_id)
    return jsonify({'response': response})

# Test route to debug API calls
@app.route('/test-apis')
def test_apis():
    # Test Google Places API
    places, places_error = get_places("Madurai")
    if places_error:
        places_result = f"Error fetching places: {places_error}"
    else:
        places_result = f"Places in Madurai: {', '.join(places)}"

    # Test OpenWeatherMap API
    weather, weather_error = get_weather("Madurai")
    if weather_error:
        weather_result = f"Error fetching weather: {weather_error}"
    else:
        weather_result = f"Weather in Madurai: {weather['temp']}°C, {weather['description']}"

    return jsonify({
        "places": places_result,
        "weather": weather_result
    })

if __name__ == '__main__':
    app.run(debug=True)