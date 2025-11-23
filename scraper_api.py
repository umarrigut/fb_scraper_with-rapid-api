from flask import Flask, jsonify
import requests
import time
from datetime import datetime
import re # Added this library to clean the text
import os

app = Flask(__name__)

# --- CONFIGURATION ---
RAPID_API_KEY = os.getenv('RAPID_API_KEY')
RAPID_API_HOST = "facebook-scraper3.p.rapidapi.com"

# Validate that API key is set
if not RAPID_API_KEY:
    raise ValueError("RAPID_API_KEY environment variable is required. Please set it in Railway or your environment.")

# Your Keywords
KEYWORDS = [
    "Phil Lyman",
    "Phil Lieman",
    "Recapture Investment Group",
    "Utah election fraud",
    "Diedre Henderson",
    "Sean Reyes",
    "Tim Ballard",
    "Just Phil Lyman"
]

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({"status": "ok", "message": "Facebook Scraper API is running"}), 200

@app.route('/scrape-facebook', methods=['GET'])
def run_scraper():
    print("--- Starting Scrape Job ---")
    clean_data_list = []
    
    url = f"https://{RAPID_API_HOST}/search/posts"
    
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": RAPID_API_HOST
    }

    for keyword in KEYWORDS:
        print(f"Searching for: '{keyword}'...")
        
        # --- EXACT PARAMETERS YOU REQUESTED ---
        querystring = {
            "query": keyword,
            "recent_posts": "true",     # Forces recent data
            "date_filter": "past_24h"   # Filters for the last 24 hours
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            
            if response.status_code == 200:
                data = response.json()
                
                if "results" in data and isinstance(data["results"], list):
                    raw_posts = data["results"]
                    
                    for post in raw_posts:
                        try:
                            # --- 1. DATE HANDLING ---
                            # Get raw timestamp (No math/subtraction, just raw data)
                            timestamp = post.get('timestamp', time.time())
                            iso_date = datetime.fromtimestamp(timestamp).isoformat()

                            # --- 2. EXTRACT LIKES ---
                            reactions = post.get('reactions', {})
                            like_count = reactions.get('like', 0)
                            if like_count == 0:
                                like_count = post.get('reactions_count', 0)

                            # --- 3. TEXT CLEANING (Matches your N8N logic) ---
                            raw_text = post.get('message_rich', post.get('message', ''))
                            if raw_text is None:
                                raw_text = ''
                            # Remove URLs
                            clean_text = re.sub(r'https?://\S+', '', raw_text) 
                            # Replace newlines with spaces
                            clean_text = clean_text.replace('\n', ' ')
                            # Remove extra spaces
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()

                            # --- 4. SKIP EMPTY POSTS ---
                            # Only process posts that have actual text content
                            if not clean_text or clean_text.strip() == '':
                                continue
                            
                            # --- 5. BUILD FINAL OBJECT ---
                            # This matches EXACTLY what your Code Node expects
                            clean_post = {
                                'post_text': clean_text,
                                'post_id': post.get('post_id'),
                                'post_url': post.get('url'),
                                'author_name': post.get('author', {}).get('name', 'Unknown'),
                                'created_at': iso_date,
                                'likes': like_count,
                                'comments': post.get('comments_count', 0),
                                'shares': post.get('reshare_count', 0),
                                'views': post.get('video_view_count', 0),
                                'found_via_keyword': keyword
                            }
                            
                            clean_data_list.append(clean_post)
                            
                        except Exception as e:
                            print(f"Error parsing a post: {e}")

            elif response.status_code == 429:
                print("Rate limit hit! Waiting 10 seconds...")
                time.sleep(10)
            else:
                print(f"Error {response.status_code} for {keyword}")

        except Exception as e:
            print(f"Script Error on {keyword}: {str(e)}")

        # Pause to prevent blocking
        time.sleep(2) 

    print(f"--- Job Done. Returning {len(clean_data_list)} posts. ---")
    return jsonify(clean_data_list)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
