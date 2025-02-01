import os
from flask import Flask, render_template, request, jsonify
import requests
import random  # Controls probability of NPC introduction

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

        # Randomly decide whether to introduce an NPC (30% chance)
        introduce_npc = random.random() < 0.3  

        # AI prompt instructions
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
                " Introduce a new character naturally within the scene, limiting their dialogue to at most two lines. "
                "Ensure the options still appear at the END of the response after the scenario."
            )

        payload = {
            "model": "mistral-small",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 250  # Further reduced token count for brevity
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

        # Format user choice naturally (removing "You: <number>.")
        formatted_user_input = user_input.lstrip("0123456789. ")  # Remove leading number and period
        formatted_user_input = f"You {formatted_user_input[0].lower()}{formatted_user_input[1:]}"  # Convert to natural sentence

        ai_response = get_ai_response(f"{formatted_user_input}. What happens next?")

        # Ensure scenario and options are extracted correctly
        scenario_text = ai_response.strip()
        options_text = ""

        # Strictly enforce separation between scenario and options
        if "\nOptions:" in scenario_text:
            split_parts = scenario_text.rsplit("\nOptions:", 1)  # Ensures only the last occurrence is split
            scenario_text = split_parts[0].strip()
            options_text = split_parts[1].strip() if len(split_parts) > 1 else ""

        # Remove any intro messages like "Start" or "Welcome to the game!"
        scenario_text = scenario_text.replace("Start", "").replace("Welcome to the game!", "").strip()

        # Remove all occurrences of "Scenario:" in the text
        scenario_text = scenario_text.replace("Scenario:", "").strip()

        # Ensure options are properly formatted and remove numbering
        options = [opt.strip("- ").strip().lstrip("0123456789. ") for opt in options_text.split("\n") if opt.strip()]

        # Remove extra words if AI formats incorrectly
        options = [opt for opt in options if "Options" not in opt]

        # Ensure at least 3-4 options are valid (removing any incomplete ones)
        options = [opt for opt in options if len(opt.split()) > 3]  # Ensures full sentences

        # If options are missing, retry extraction from the last few sentences of the scenario
        if len(options) < 3:
            scenario_lines = scenario_text.split(". ")
            if len(scenario_lines) > 2:
                options = [line.strip() for line in scenario_lines[-2:] if len(line.split()) > 3]

        # If options are still insufficient, provide fallback choices
        while len(options) < 3:
            options.append(random.choice(["Explore further", "Look around carefully", "Wait and observe"]))

        return jsonify({"scenario": scenario_text, "options": options[:4]})

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"scenario": "Server error. Please try again.", "options": ["Explore further", "Look around carefully", "Wait and observe"]}), 500

if __name__ == "__main__":
    app.run(debug=True)
