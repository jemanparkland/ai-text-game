import os
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Retrieve API key from environment variables
API_KEY = os.getenv("API_KEY")

# Mistral API URL
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Store game state per session
user_game_state = {}

# Function to get AI response with clear scenario and options separation
def get_ai_response(session_id, user_input):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        # Retrieve or initialize game state
        if session_id not in user_game_state:
            user_game_state[session_id] = [
                {"role": "system", "content": "You are a text adventure game master. Ensure responses strictly separate the scenario from the multiple-choice options. The options should not be embedded inside the scenario."},
                {"role": "user", "content": "Start the adventure."}
            ]

        # Append user input to game state
        user_game_state[session_id].append({"role": "user", "content": user_input})

        payload = {
            "model": "mistral-small",
            "messages": user_game_state[session_id],
            "max_tokens": 250
        }

        response = requests.post(MISTRAL_API_URL, headers=headers, json=payload)

        if response.status_code == 200:
            ai_response = response.json()["choices"][0]["message"]["content"]

            # Append AI response to conversation history
            user_game_state[session_id].append({"role": "assistant", "content": ai_response})

            # Ensure proper separation of scenario and options
            if "\nOptions:\n" in ai_response:
                scenario_text, options_text = ai_response.split("\nOptions:\n", 1)
                options = [opt.strip("- ").strip() for opt in options_text.split("\n") if opt.strip()]
            else:
                # Fallback: Extract options using alternative pattern
                lines = ai_response.split("\n")
                scenario_text = "\n".join([line for line in lines if not line.lstrip().startswith("-")])
                options = [line.lstrip("-").strip() for line in lines if line.lstrip().startswith("-")]

            # Ensure at least 2-4 options exist
            if len(options) < 2:
                options = ["Speak with a stranger", "Search the area", "Wait and observe"]

            return scenario_text.strip(), options

        else:
            print(f"Error: {response.status_code} - {response.text}")
            return "Error: Unable to generate response from AI.", ["Retry"]

    except Exception as e:
        print(f"Server error: {e}")
        return "Error: Something went wrong.", ["Retry"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/play", methods=["POST"])
def play():
    try:
        data = request.json
        user_input = data.get("choice", "").strip()
        session_id = request.remote_addr  # Use IP as a simple session ID

        if not user_input:
            return jsonify({"scenario": "Please enter a valid action.", "options": []})

        scenario_text, options = get_ai_response(session_id, f"Player chose to: {user_input}. Update the storyline accordingly and provide 2-4 clearly separated choices.")

        return jsonify({"scenario": scenario_text, "options": options})

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"scenario": "Server error. Please try again.", "options": ["Retry"]}), 500

if __name__ == "__main__":
    app.run(debug=True)
