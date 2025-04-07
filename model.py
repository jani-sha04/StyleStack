import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle
import os
from datetime import datetime, timedelta

class ChatbotModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.classifier = LogisticRegression()
        self.intents = [
            "organize_wardrobe", "outfit_suggestion", "weather_query", "general_help"
        ]
        self.model_file = "chatbot_model.pkl"
        
        # Expanded training data for wardrobe-related intents
        self.training_data = {
            "organize_wardrobe": [
                "organize my wardrobe", "where should my clothes go", "sort my closet",
                "how should I arrange my clothes", "organize my stuff", "tidy up my wardrobe",
                "where do I put my shirts", "arrange my dresses", "organize by color",
                "how to sort my shoes"
            ],
            "outfit_suggestion": [
                "what should I wear", "suggest an outfit", "what to wear tomorrow",
                "recommend something for work", "outfit for a party", "what’s good for a date",
                "casual outfit ideas", "formal wear suggestion", "what to wear in the rain",
                "outfit for a meeting"
            ],
            "weather_query": [
                "what’s the weather like", "is it going to rain", "how’s the weather today",
                "weather tomorrow", "should I wear a jacket", "is it cold outside",
                "what’s the forecast", "will it be sunny", "weather this weekend",
                "how warm is it today"
            ],
            "general_help": [
                "help me", "what can you do", "how does this work", "tell me more",
                "I need assistance", "how do I use this", "what’s this app for",
                "can you assist me", "explain the features", "I’m confused"
            ]
        }
        
        # Train the model if not already trained
        if not os.path.exists(self.model_file):
            self.train_model()
        else:
            self.load_model()

    def train_model(self):
        # Prepare training data
        X = []
        y = []
        for intent, examples in self.training_data.items():
            X.extend(examples)
            y.extend([intent] * len(examples))
        
        # Vectorize and train
        X_vectorized = self.vectorizer.fit_transform(X)
        self.classifier.fit(X_vectorized, y)
        
        # Save the model
        with open(self.model_file, 'wb') as f:
            pickle.dump({'vectorizer': self.vectorizer, 'classifier': self.classifier}, f)
        print("Chatbot model trained and saved.")

    def load_model(self):
        with open(self.model_file, 'rb') as f:
            data = pickle.load(f)
            self.vectorizer = data['vectorizer']
            self.classifier = data['classifier']
        print("Chatbot model loaded.")

    def predict_intent(self, query):
        query_vectorized = self.vectorizer.transform([query.lower()])
        intent = self.classifier.predict(query_vectorized)[0]
        return intent

    def generate_response(self, query, user_data):
        intent = self.predict_intent(query)
        query_lower = query.lower()

        if intent == "organize_wardrobe":
            from app import organize_wardrobe  # Import here to avoid circular import
            org_result = organize_wardrobe(user_data["id"])
            return org_result["message"]

        elif intent == "outfit_suggestion":
            from app import generate_outfit_suggestions  # Import here to avoid circular import
            occasions = {"work": "work", "formal": "formal", "casual": "casual", "athletic": "athletic"}
            detected_occasion = next((occ for key, occ in occasions.items() if key in query_lower), "casual")
            date_str = datetime.now().strftime('%Y-%m-%d')
            if "tomorrow" in query_lower:
                date_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            outfits = generate_outfit_suggestions(user_data["id"], detected_occasion, date_str, 1)
            if outfits:
                outfit = outfits[0]
                items_list = ", ".join([f"{item['colors'][0]} {item['category']}" for item in outfit["items"]])
                return f"For {detected_occasion} on {date_str}, considering {outfit['weather']['conditions']} weather, I suggest: {items_list}. {outfit['description']}"
            return "I need more items in your wardrobe to suggest an outfit. Please upload some clothes!"

        elif intent == "weather_query":
            from app import get_weather_forecast  # Import here to avoid circular import
            date_str = datetime.now().strftime('%Y-%m-%d') if "today" in query_lower or "now" in query_lower else (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            weather = get_weather_forecast("user_location", date_str)
            return f"The weather on {date_str}: {weather['temp']}°F, {weather['conditions']}. {weather['recommendation']}"

        else:  # general_help
            return "I can help with outfit suggestions, wardrobe organization, or weather-based advice. What do you need?"

if __name__ == "__main__":
    # Train the model when running this file directly
    model = ChatbotModel()
    model.train_model()