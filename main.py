import os
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Retrieve API key from environment variables
API_KEY = os.getenv("API_KEY")

# Mistral API URL
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Function to get AI response from Mistral API
def get_ai_response(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "mistral-small",
            "messages": [
                {"role": "system", "content": "You are a text adventure game master. Generate a short scenario, followed by exactly 3-4 suggested player actions. Format them clearly under 'Options:'. Ensure there are always options."},
                {"role": "user", "content": prompt}
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
            return jsonify({"scenario": "Please enter a valid action.", "options": []})

        ai_response = get_ai_response(f"Player chose to: {user_input}. What happens next?")

        # Extract the scenario and multiple-choice options
        scenario_text, options_text = ai_response.split("\nOptions:", 1) if "\nOptions:" in ai_response else (ai_response, "")
        options = [opt.strip("- ").strip() for opt in options_text.split("\n") if opt.strip()] or ["Explore", "Look around", "Wait"]

        return jsonify({"scenario": scenario_text, "options": options})

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"scenario": "Server error. Please try again.", "options": ["Explore", "Look around", "Wait"]}), 500

if __name__ == "__main__":
    app.run(debug=True)
