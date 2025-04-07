from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
from datetime import datetime
import numpy as np
import json
from werkzeug.utils import secure_filename
import logging
import random
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.resnet50 import preprocess_input
import cv2
import requests
from model import ChatbotModel  # Import the new chatbot model

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE_PATH = 'database'
WEATHER_API_KEY = "your_weather_api_key"  # Replace with your actual API key

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_PATH, exist_ok=True)
os.makedirs(os.path.join(DATABASE_PATH, 'users'), exist_ok=True)
os.makedirs(os.path.join(DATABASE_PATH, 'outfits'), exist_ok=True)

# Load AI Models
try:
    image_model = ResNet50(weights='imagenet', include_top=False, pooling='avg')
    chatbot_model = ChatbotModel()  # Initialize our custom chatbot model
    models_loaded = True
    logger.info("AI models loaded successfully")
except Exception as e:
    models_loaded = False
    logger.error(f"Error loading AI models: {e}")

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_data_path(user_id):
    return os.path.join(DATABASE_PATH, 'users', f"{user_id}.json")

def load_user_data(user_id):
    user_path = get_user_data_path(user_id)
    if os.path.exists(user_path):
        with open(user_path, 'r') as f:
            return json.load(f)
    return {
        "id": user_id,
        "wardrobe": [],
        "outfits": [],
        "preferences": {"style_preferences": [], "color_preferences": [], "favorite_occasions": []},
        "chatbot_history": [],
        "organization": {"closet_sections": [], "last_organized": None}
    }

def save_user_data(user_id, data):
    with open(get_user_data_path(user_id), 'w') as f:
        json.dump(data, f)

def generate_image_embedding(img_path):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        features = image_model.predict(x)
        return features.flatten().tolist()
    except Exception as e:
        logger.error(f"Error generating image embedding: {e}")
        return []

def get_colors(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return ["unknown"]
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pixels = img.reshape(-1, 3)
    pixels = np.float32(pixels)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    k = 3
    _, labels, palette = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    dominant_color = palette[np.argmax(counts)]
    r, g, b = dominant_color
    color_map = {
        "red": (r > 150 and g < 100 and b < 100),
        "green": (r < 100 and g > 150 and b < 100),
        "blue": (r < 100 and g < 100 and b > 150),
        "yellow": (r > 150 and g > 150 and b < 100),
        "purple": (r > 100 and g < 100 and b > 100),
        "orange": (r > 150 and g > 100 and b < 100),
        "pink": (r > 150 and g < 100 and b > 100),
        "black": (r < 50 and g < 50 and b < 50),
        "white": (r > 200 and g > 200 and b > 200),
        "gray": (r > 50 and r < 200 and g > 50 and g < 200 and b > 50 and b < 200 and max(r, g, b) - min(r, g, b) < 50)
    }
    for color_name, condition in color_map.items():
        if condition:
            return [color_name]
    return ["other"]

def classify_clothing(img_path, filename):
    if not models_loaded:
        categories = ['tops', 'bottoms', 'dresses', 'outerwear', 'shoes', 'accessories']
        seasons = ['spring', 'summer', 'fall', 'winter']
        occasions = ['casual', 'work', 'formal', 'athletic']
        name = filename.lower()
        if any(word in name for word in ['shirt', 'top', 'tee', 'blouse', 'sweater']):
            category = 'tops'
        elif any(word in name for word in ['pants', 'jeans', 'shorts', 'skirt']):
            category = 'bottoms'
        elif any(word in name for word in ['dress', 'gown']):
            category = 'dresses'
        elif any(word in name for word in ['jacket', 'coat', 'hoodie']):
            category = 'outerwear'
        elif any(word in name for word in ['shoe', 'sneaker', 'boot']):
            category = 'shoes'
        elif any(word in name for word in ['hat', 'scarf', 'glove', 'necklace', 'earring']):
            category = 'accessories'
        else:
            category = random.choice(categories)
        selected_seasons = random.sample(seasons, k=random.randint(1, 4))
        selected_occasions = random.sample(occasions, k=random.randint(1, 3))
        return {
            "category": category,
            "seasons": selected_seasons,
            "occasions": selected_occasions,
            "colors": get_colors(img_path) if models_loaded else [random.choice(['black', 'white', 'blue', 'red', 'green', 'yellow', 'other'])],
            "tags": []
        }
    else:
        embedding = generate_image_embedding(img_path)
        colors = get_colors(img_path)
        result = classify_clothing(img_path, filename)  # Recursive call for fallback
        result["embedding"] = embedding
        result["colors"] = colors
        return result

def get_weather_forecast(location, date_str):
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&dt={date_str}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            forecast = data['forecast']['forecastday'][0]['day']
            return {
                "temp": forecast['avgtemp_f'],
                "conditions": forecast['condition']['text'].lower(),
                "recommendation": "Adjust based on weather conditions."
            }
        else:
            logger.error(f"Weather API error: {response.status_code}")
            return {"temp": 70, "conditions": "unknown", "recommendation": "versatile clothing"}
    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        return {"temp": 70, "conditions": "unknown", "recommendation": "versatile clothing"}

def organize_wardrobe(user_id):
    user_data = load_user_data(user_id)
    wardrobe = user_data["wardrobe"]
    if not wardrobe:
        return {"message": "Wardrobe is empty", "sections": []}

    sections = {
        "Daily Wear": {"categories": ["tops", "bottoms"], "seasons": ["spring", "summer"], "items": []},
        "Seasonal": {"categories": ["outerwear"], "seasons": ["fall", "winter"], "items": []},
        "Special Occasion": {"categories": ["dresses"], "seasons": ["all"], "items": []},
        "Accessories": {"categories": ["accessories", "shoes"], "seasons": ["all"], "items": []}
    }

    for item in wardrobe:
        placed = False
        for section_name, section in sections.items():
            if item["category"] in section["categories"]:
                if "all" in section["seasons"] or any(s in item["seasons"] for s in section["seasons"]):
                    section["items"].append({
                        "id": item["id"],
                        "name": item["name"],
                        "category": item["category"],
                        "color": item["colors"][0],
                        "placement": f"{section_name} Section"
                    })
                    placed = True
                    break
        if not placed:
            sections["Daily Wear"]["items"].append({
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "color": item["colors"][0],
                "placement": "Daily Wear Section (default)"
            })

    user_data["organization"]["closet_sections"] = [
        {"name": name, "items": data["items"]} for name, data in sections.items()
    ]
    user_data["organization"]["last_organized"] = datetime.now().isoformat()
    save_user_data(user_id, user_data)

    organization_message = "I've organized your wardrobe! Here's where your clothes should go:\n"
    for section_name, section in sections.items():
        if section["items"]:
            item_names = ", ".join([item["name"] for item in section["items"]])
            organization_message += f"- {section_name}: {item_names}\n"
    return {"message": organization_message, "sections": user_data["organization"]["closet_sections"]}

def generate_outfit_suggestions(user_id, occasion, date_str, num_outfits=3):
    user_data = load_user_data(user_id)
    if not user_data["wardrobe"]:
        return []

    weather = get_weather_forecast("user_location", date_str)
    occasion_items = [item for item in user_data["wardrobe"] if occasion in item["occasions"]]
    if len(occasion_items) < 4:
        occasion_items = user_data["wardrobe"]

    seasons = ["spring", "summer"] if weather["temp"] > 65 else ["fall", "winter"]
    season_items = [item for item in occasion_items if any(season in item["seasons"] for season in seasons)]
    items_pool = season_items if len(season_items) >= 4 else occasion_items

    categories = {
        "casual": ["tops", "bottoms", "shoes"],
        "work": ["tops", "bottoms", "shoes"],
        "formal": ["dresses", "shoes", "accessories"],
        "athletic": ["tops", "bottoms", "shoes"]
    }
    target_cats = categories.get(occasion, ["tops", "bottoms", "shoes"])

    outfits = []
    for _ in range(min(num_outfits, len(items_pool) // len(target_cats))):
        outfit = {"id": str(uuid.uuid4()), "occasion": occasion, "date": date_str, "weather": weather, "items": []}
        for category in target_cats:
            cat_items = [item for item in items_pool if item["category"] == category]
            if cat_items:
                chosen_item = random.choice(cat_items)
                outfit["items"].append(chosen_item)
                items_pool.remove(chosen_item)
        outfit["score"] = len(outfit["items"]) / len(target_cats)
        colors = ", ".join(set([item["colors"][0] for item in outfit["items"]]))
        outfit["description"] = f"{occasion.capitalize()} outfit for {weather['conditions']} weather ({weather['temp']}°F) with {colors} pieces."
        outfits.append(outfit)

    outfits.sort(key=lambda x: x["score"], reverse=True)
    return outfits

def process_chatbot_query(user_id, query):
    user_data = load_user_data(user_id)
    user_data["chatbot_history"].append({"sender": "user", "message": query, "timestamp": datetime.now().isoformat()})

    # Use the chatbot model to predict intent and generate response
    response = chatbot_model.generate_response(query, user_data)

    user_data["chatbot_history"].append({"sender": "assistant", "message": response, "timestamp": datetime.now().isoformat()})
    if len(user_data["chatbot_history"]) > 100:
        user_data["chatbot_history"] = user_data["chatbot_history"][-100:]
    save_user_data(user_id, user_data)
    return response

# API Routes
@app.route('/')
def serve_frontend():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/organize/<user_id>', methods=['GET'])
def organize_wardrobe_route(user_id):
    result = organize_wardrobe(user_id)
    return jsonify(result)

@app.route('/api/chat/<user_id>', methods=['POST'])
def chat(user_id):
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "No query provided"}), 400
    response = process_chatbot_query(user_id, query)
    return jsonify({"response": response})

@app.route('/api/upload/<user_id>', methods=['POST'])
def upload_file(user_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{os.path.splitext(filename)[0]}_{uuid.uuid4().hex}{os.path.splitext(filename)[1]}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)

    classification = classify_clothing(filepath, filename)
    user_data = load_user_data(user_id)
    item_id = str(uuid.uuid4())

    new_item = {
        "id": item_id,
        "name": os.path.splitext(filename)[0],
        "filepath": filepath,
        "image_url": f"/api/image/{unique_filename}",
        "upload_date": datetime.now().isoformat(),
        "category": classification["category"],
        "colors": classification["colors"],
        "seasons": classification["seasons"],
        "occasions": classification["occasions"],
        "tags": classification["tags"]
    }
    user_data["wardrobe"].append(new_item)
    save_user_data(user_id, user_data)

    org_result = organize_wardrobe(user_id)
    return jsonify({"status": "success", "message": "File uploaded and wardrobe organized", "item": new_item, "organization": org_result})

@app.route('/api/image/<filename>')
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/wardrobe/<user_id>')
def get_wardrobe(user_id):
    user_data = load_user_data(user_id)
    category = request.args.get('category', 'all')
    color = request.args.get('color', 'all')
    season = request.args.get('season', 'all')
    occasion = request.args.get('occasion', 'all')

    filtered_items = user_data["wardrobe"]
    if category != 'all':
        filtered_items = [item for item in filtered_items if item["category"] == category]
    if color != 'all':
        filtered_items = [item for item in filtered_items if color in item["colors"]]
    if season != 'all':
        filtered_items = [item for item in filtered_items if season in item["seasons"]]
    if occasion != 'all':
        filtered_items = [item for item in filtered_items if occasion in item["occasions"]]

    return jsonify({"wardrobe": filtered_items, "total_items": len(user_data["wardrobe"]), "filtered_count": len(filtered_items)})

@app.route('/api/wardrobe/<user_id>/<item_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_wardrobe_item(user_id, item_id):
    user_data = load_user_data(user_id)
    item_index = next((i for i, item in enumerate(user_data["wardrobe"]) if item["id"] == item_id), None)
    if item_index is None:
        return jsonify({"error": "Item not found"}), 404

    if request.method == 'GET':
        return jsonify(user_data["wardrobe"][item_index])
    elif request.method == 'PUT':
        data = request.json
        allowed_fields = ["name", "category", "colors", "seasons", "occasions", "tags"]
        for field in allowed_fields:
            if field in data:
                user_data["wardrobe"][item_index][field] = data[field]
        save_user_data(user_id, user_data)
        return jsonify({"status": "success", "message": "Item updated", "item": user_data["wardrobe"][item_index]})
    elif request.method == 'DELETE':
        item = user_data["wardrobe"][item_index]
        if "filepath" in item and os.path.exists(item["filepath"]):
            try:
                os.remove(item["filepath"])
            except Exception as e:
                logger.warning(f"Could not delete file {item['filepath']}: {e}")
        del user_data["wardrobe"][item_index]
        save_user_data(user_id, user_data)
        return jsonify({"status": "success", "message": "Item deleted"})

@app.route('/api/outfits/<user_id>', methods=['GET', 'POST'])
def manage_outfits(user_id):
    if request.method == 'GET':
        occasion = request.args.get('occasion', 'casual')
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        num_outfits = int(request.args.get('count', 3))
        outfits = generate_outfit_suggestions(user_id, occasion, date, num_outfits)
        return jsonify({"outfits": outfits, "count": len(outfits)})
    elif request.method == 'POST':
        data = request.json
        user_data = load_user_data(user_id)
        if not data or "items" not in data:
            return jsonify({"error": "Missing outfit data"}), 400
        outfit_id = str(uuid.uuid4())
        outfit = {
            "id": outfit_id,
            "name": data.get("name", f"Outfit {len(user_data['outfits']) + 1}"),
            "occasion": data.get("occasion", "casual"),
            "date_created": datetime.now().isoformat(),
            "items": data["items"]
        }
        user_data["outfits"].append(outfit)
        save_user_data(user_id, user_data)
        return jsonify({"status": "success", "outfit": outfit})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)