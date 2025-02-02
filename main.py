import os
import sqlite3
import re  # Import regex for dialogue formatting
from flask import Flask, render_template, request, jsonify
import requests
import random  # Controls probability of NPC introduction

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Retrieve API key from environment variables
API_KEY = os.getenv("API_KEY")

# Mistral API URL
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Store conversation history to maintain story continuity
conversation_history = []

# ✅ Function to query images from the SQLite database
def get_image_suggestions(scenario_text):
    db_path = "data/images.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = scenario_text.lower().split()
    cursor.execute("SELECT filename FROM images WHERE keyword IN ({seq})".format(
        seq=','.join(['?']*len(keywords))), keywords)

    images = cursor.fetchall()
    conn.close()

    # Default to "unknown.png" if no matches are found
    selected_images = {
        "environment": "unknown.png",
        "item": "unknown.png",
        "character": "unknown.png"
    }

    if images:
        selected_images["environment"] = images[0][0] if len(images) > 0 else "unknown.png"
        selected_images["item"] = images[1][0] if len(images) > 1 else "unknown.png"
        selected_images["character"] = images[2][0] if len(images) > 2 else "unknown.png"

    return selected_images

# ✅ Function to format NPC dialogues properly
def format_npc_dialogue(text):
    """Ensures only properly structured NPC dialogues are formatted"""
    return re.sub(r'(\b[A-Za-z]+):\s*"([^"]+)"', r'<span class="npc-dialogue"><strong>\1:</strong> “\2”</span>', text)

# Function to get AI response from Mistral API
def get_ai_response(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        # Randomly decide whether to introduce an NPC (40% chance)
        introduce_npc = random.random() < 0.4  

        # Construct a rolling history for context
        history_context = "\n".join(conversation_history[-5:])  # Keep last 5 exchanges for continuity

        # AI prompt instructions (Enforce text length & proper formatting)
        system_prompt = (
            "You are a text adventure game master. Generate a short, engaging scenario (~30% shorter than usual) "
            "that follows logically from the player's input. Keep NPC dialogue to a MAXIMUM of 1-2 exchanges before presenting options. "
            "Ensure the response is no longer than 150 words to keep pacing tight. "
            "STRICTLY separate the scenario from player options. NEVER embed choices inside the scenario text. "
            "Options must be listed in a new paragraph starting with 'Options:'. "
            "Each choice must be a standalone sentence without numbering or bullets."
            "DO NOT append extra words after 'Options:'. "
            "DO NOT include 'Scenario:' or any introduction text like 'Welcome to the game!'."
        )

        if introduce_npc:
            system_prompt += (
                " Introduce an NPC naturally but limit their dialogue to **1-2 lines**. "
                "Ensure 'Options:' is **always placed at the end**."
            )

        # Format final AI input
        final_prompt = f"Previous Events:\n{history_context}\n\nCurrent Action: {prompt}\n\nWhat happens next?"

        payload = {
            "model": "mistral-small",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt}
            ],
            "max_tokens": 250
        }

        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return "Error: Unable to generate response from AI."

    except Exception as e:
        print(f"Server error: {e}")
        return "Error: Something went wrong."

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play", methods=["POST"])
def play():
    try:
        data = request.json
        user_input = data.get("choice", "").strip()

        if not user_input:
            return jsonify({
                "scenario": "Please enter a valid action.",
                "options": [],
                "images": {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}
            })

        formatted_user_input = user_input.lstrip("0123456789. ")
        formatted_user_input = f"You {formatted_user_input[0].lower()}{formatted_user_input[1:]}"

        ai_response = get_ai_response(f"{formatted_user_input}. What happens next?")

        scenario_text = ai_response.strip()
        options_text = ""

        # ✅ Enforce proper scenario and option separation
        if "\nOptions:" in scenario_text:
            split_parts = scenario_text.rsplit("\nOptions:", 1)
            scenario_text = split_parts[0].strip()
            options_text = split_parts[1].strip() if len(split_parts) > 1 else ""

        # ✅ Clean up response formatting
        scenario_text = scenario_text.replace("Start", "").replace("Welcome to the game!", "").strip()
        scenario_text = scenario_text.replace("Scenario:", "").strip()

        # ✅ Format NPC dialogue properly
        scenario_text = format_npc_dialogue(scenario_text)

        # ✅ Ensure options are clean and formatted correctly
        options = [opt.strip("- ").strip().lstrip("0123456789. ") for opt in options_text.split("\n") if opt.strip()]
        options = [opt for opt in options if "Options" not in opt]

        # ✅ Ensure at least 3 options are present
        options = [opt for opt in options if len(opt.split()) > 3]
        while len(options) < 3:
            options.append(random.choice(["Explore further", "Look around carefully", "Wait and observe"]))

        # ✅ Get separate images for environment, item, and character
        images = get_image_suggestions(scenario_text)

        # 🔹 Debugging: Print selected images to verify Flask is working correctly
        print(f"DEBUG: Selected images: {images}")

        # ✅ Maintain history while keeping it concise
        conversation_history.append(f"Player: {formatted_user_input}\nResponse: {scenario_text}")
        conversation_history[-10:]  # Keep only the last 10 exchanges

        return jsonify({"scenario": scenario_text, "options": options[:4], "images": images})

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({
            "scenario": "Server error. Please try again.",
            "options": ["Explore further", "Look around carefully", "Wait and observe"],
            "images": {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
