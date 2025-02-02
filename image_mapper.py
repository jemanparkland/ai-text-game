import sqlite3
import os
import re

# Database path
db_path = os.path.join("data", "images.db")

# Function to retrieve images based on scenario description
def get_image_suggestions(scene_description):
    """
    Given a scene description, return the best-matching images for environment, items, and characters.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Convert description to lowercase
    scene_description = scene_description.lower()

    # Extract words from scene description
    words = re.findall(r'\b\w+\b', scene_description)

    # Initialize image categories
    images = {"environment": "unknown.png", "item": "unknown.png", "character": "unknown.png"}

    for word in words:
        cursor.execute("SELECT filename FROM images WHERE keyword = ? LIMIT 1", (word,))
        result = cursor.fetchone()
        
        if result:
            filename = result[0]
            if any(x in filename for x in ["tree", "rock", "water", "lava", "castle", "cave"]):
                images["environment"] = filename
            elif any(x in filename for x in ["sword", "staff", "shield", "book", "potion"]):
                images["item"] = filename
            elif any(x in filename for x in ["wizard", "dragon", "orc", "skeleton", "undead", "goblin"]):
                images["character"] = filename

    conn.close()
    return images
