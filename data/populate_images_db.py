import sqlite3
import re

# Create database connection
conn = sqlite3.connect("images.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT UNIQUE,
    category TEXT,
    keywords TEXT
)
""")

# Image categorization based on common filename patterns
CATEGORY_MAPPING = {
    "dngn_|castle|ruins|dungeon|cave|forest|swamp|lava|desert|village|city|ice|volcano|tavern|altar": "environment",
    "sword|dagger|axe|shield|potion|scroll|staff|wand|key|gold|treasure|armor|ring|orb|rune|stone": "item",
    "goblin|orc|troll|dragon|lich|wizard|knight|demon|vampire|guardian|mummy|skeleton|elf|merchant|bandit": "character"
}

# List of filenames provided by the user (shortened for example)
image_filenames = [
    "dragon.png", "wizard_blue.png", "gold_pile.png", "dngn_stone_arch.png",
    "sword.png", "shield2.png", "goblin.png", "orc_warlord.png"
]  # Replace with the full list

# Function to determine category
def determine_category(filename):
    for pattern, category in CATEGORY_MAPPING.items():
        if re.search(pattern, filename, re.IGNORECASE):
            return category
    return "unknown"

# Insert images into the database
for filename in image_filenames:
    category = determine_category(filename)
    keywords = filename.replace("_", " ").replace(".png", "")
    
    cursor.execute("INSERT OR IGNORE INTO images (filename, category, keywords) VALUES (?, ?, ?)",
                   (filename, category, keywords))

# Commit and close
conn.commit()
conn.close()

print("Database population complete!")
