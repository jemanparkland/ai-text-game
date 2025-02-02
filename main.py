import os
import sqlite3
import re
from flask import Flask, render_template, request, jsonify
import requests
import random  
import time  # For retrying API calls on rate limits

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Retrieve API key from environment variables
API_KEY = os.getenv("API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

conversation_history = []

# ✅ Query images from the SQLite database
def get_image_suggestions(scenario_text):
    db_path = "data/images.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    keywords = scenario_text.lower().split()
    cursor.execute("SELECT filename FROM images WHERE keyword IN ({seq})".format(
        seq=','.join(['?']*len(keywords))), keywords)

    images = cursor.fetchall()
    conn.close()

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

# ✅ Format NPC dialogue into block quotes (Soft limit: 1 NPC quote)
def format_npc_dialogue(text):
    """Ensures NPC dialogue is formatted and applies a soft limit of one quote per scenario."""
    matches = re.findall(r'(\b[A-Za-z]+):\s*"([^"]+)"', text)

    if matches:
        # Keep only the first valid NPC quote
        formatted_text = re.sub(
            r'(\b[A-Za-z]+):\s*"([^"]+)"', 
            r'<span class="npc-dialogue"><strong>\1:</strong> “\2”</span>', 
            text, count=1
        )
        # Remove any additional quotes beyond the first one
        formatted_text = re.sub(r'(\b[A-Za-z]+):\s*"([^"]+)"', r'\1: “...”', formatted_text)
        return formatted_text
    return text

# ✅ Mistral API Request with retry mechanism (Handles 429 Rate Limits)
def request_mistral(payload):
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.post(MISTRAL_API_URL, headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }, json=payload)

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()

            elif response.status_code == 429:  # Rate limit exceeded
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue  

            else:
                print(f"Error: {response.status_code} - {response.text}")
                return None  

        except Exception as e:
            print(f"Server error: {e}")
            return None  
    return None  

# ✅ Generate AI scenario **without** options, enforcing the soft limit on NPC quotes
def get_scenario(prompt):
    history_context = "\n".join(conversation_history[-10:])  

    system_prompt = (
        "You are a text adventure game master. Generate a **complete, standalone** scenario that follows logically from the player's input. "
        "Limit NPC dialogue to **one short response only (1-2 lines max)** before stopping. "
        "Ensure the scenario is **no longer than 120 words** to maintain fast pacing. "
        "STRICTLY separate the scenario from player options. DO NOT include player choices, 'Options:', or action prompts. "
        "DO NOT use repetitive phrases like 'To be continued' or 'What happens next?'. "
        "NEVER repeat 'Your adventure has begun' or similar redundant statements."
    )

    final_prompt = f"Previous Events:\n{history_context}\n\nCurrent Action: {prompt}\n\nWhat happens next?"

    payload = {
        "model": "mistral-small",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_prompt}
        ],
        "max_tokens": 200
    }

    scenario_text = request_mistral(payload)

    if scenario_text:
        return scenario_text.split("\nOptions:")[0].strip()  # Ensure "Options:" never appears in scenario
    return None

# ✅ Generate AI-generated options **separately**
def get_options(scenario_text):
    system_prompt = (
        "You are a text adventure game master. Generate **exactly 3-4 concise choices** based on the scenario. "
        "Each choice must be **short, distinct, and action-driven** (10 words max). "
        "DO NOT include 'Options:', numbers, or bullets. "
        "DO NOT suggest passive options like 'Wait and observe'."
    )

    final_prompt = f"Scenario:\n{scenario_text}\n\nWhat are the possible actions the player can take?"

    payload = {
        "model": "mistral-small",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": final_prompt}
        ],
        "max_tokens": 80
    }

    options_text = request_mistral(payload)

    if options_text:
        options = [opt.strip("- ").strip().lstrip("0123456789. ") for opt in options_text.split("\n") if opt.strip()]
        options = [opt for opt in options if len(opt.split()) <= 8]  

        while len(options) < 3:
            options.append(random.choice(["Explore further", "Look around", "Wait"]))

        return options[:4]
    return ["Explore further", "Look around", "Wait"]

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
                "options": ["Explore further", "Look around", "Wait"],
                "images": {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}
            })

        formatted_user_input = user_input.lstrip("0123456789. ")
        formatted_user_input = f"You {formatted_user_input[0].lower()}{formatted_user_input[1:]}"

        ai_scenario = get_scenario(f"{formatted_user_input}. What happens next?")
        if not ai_scenario:
            return jsonify({
                "scenario": "Error generating scenario. Please try again.",
                "options": ["Explore further", "Look around", "Wait"],
                "images": {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}
            })

        scenario_text = format_npc_dialogue(ai_scenario)

        options = get_options(scenario_text)

        images = get_image_suggestions(scenario_text)

        conversation_history.append(f"Player: {formatted_user_input}\nResponse: {scenario_text}")
        conversation_history[-10:]

        return jsonify({"scenario": scenario_text, "options": options, "images": images})

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({
            "scenario": "Server error. Please try again.",
            "options": ["Explore further", "Look around", "Wait"],
            "images": {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
