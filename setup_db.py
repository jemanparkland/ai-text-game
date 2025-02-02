import sqlite3
import os
import re

# Path to the image database
db_path = "data/images.db"

# Path to the folder containing images (Make sure this is correct)
images_folder = "static/images"

# Function to generate keywords from filenames
def extract_keywords(filename):
    filename = filename.lower().replace("_", " ").replace("-", " ").replace(".png", "")
    words = re.findall(r'\b[a-zA-Z]+\b', filename)  # Keep only letters
    return " ".join(words)  # Return as a single string for DB storage

# Get all PNG files from the images folder
image_filenames = [f for f in os.listdir(images_folder) if f.endswith(".png")]

# Connect to SQLite and create table
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create table (if not exists)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE,
        filename TEXT
    )
""")

# Prepare data for insertion
image_data = []
for filename in image_filenames:
    keyword = extract_keywords(filename)
    if keyword:  # Avoid empty keywords
        image_data.append((keyword, filename))

# Insert into database (ignore duplicates)
try:
    cursor.executemany("INSERT OR IGNORE INTO images (keyword, filename) VALUES (?, ?)", image_data)
    conn.commit()
    print(f"✅ Successfully added {len(image_data)} images to the database.")
except sqlite3.IntegrityError as e:
    print(f"⚠️ Error inserting data: {e}")

# Close connection
conn.close()
