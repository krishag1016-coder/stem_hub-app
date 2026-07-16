import sys
import os
import requests
import json
import re
from dotenv import load_dotenv

# Load your API Keys from .env
load_dotenv()

# Ensure Python can find your database configuration files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.database import supabase

# --- CONFIGURATION (Upgraded Router & Keys) ---
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_HEADERS = {
    "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}",
    "Content-Type": "application/json"
}

def query_llm(payload):
    """Sends prompt request directly to Hugging Face via API connection"""
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Hugging Face API returned status code {response.status_code}")
        print(f"Response: {response.text}")
        return None
    return response.json()

def get_ai_structured_opportunities(raw_text):
    """Feeds raw text to Llama-3 and returns perfectly structured JSON"""
    print("🧠 Asking Hugging Face (Llama-3) to parse and tag the scraped data...")
    
    # 2. Build the strict JSON-generating prompt with our clean STEM Subject list
    prompt = f"""
    You are an expert data organizer for a High School STEM Directory website.
    I am going to give you raw text scraped from a website listing student opportunities.
    
    Your job is to read this text and extract up to 3 distinct student opportunities.
    For each opportunity, you must extract:
    - Title: The name of the competition, program, or hackathon.
    - Type: Choose exactly one from ["Competitions/Hackathons", "Research & Fellowships", "Internships", "Summer Camps", "Scholarships"].
    - Subject: Choose EXACTLY ONE single broad academic field from this exact list: ["Computer Science", "Engineering", "Biology", "Chemistry", "Physics", "Mathematics", "Earth & Environmental Science", "Interdisciplinary STEM"]. You MUST NOT make up your own subject, and you MUST NOT include multiple subjects, commas, or the word "and".
    - Tags: A list of 2 to 4 specific sub-topic tags (e.g., ["Coding", "AI", "Robotics", "Astrophysics"]).
    - Deadline: If found, use YYYY-MM-DD format. If not found or vague, default to "2026-11-30".
    - Link: The website URL.
    - Description: A clear, engaging 1-2 sentence description of what the program is.
    - Is_Paid: A boolean (true or false). Set to true if there is a tuition fee, application fee, or cost to participate. Set to false if it is entirely free, offers a stipend, or is fully funded.
    
    Return ONLY a raw JSON array of objects matching this exact structure:
    [
      {{
        "Title": "Example Program",
        "Type": "Summer Camps",
        "Subject": "Physics",
        "Tags": ["Astrophysics", "Space Science"],
        "Deadline": "2026-11-30",
        "Link": "https://example.com",
        "Description": "An amazing physics camp.",
        "Is_Paid": false
      }}
    ]

    No markdown formatting, no code blocks (do not use ```json), no trailing conversational text. Just the raw JSON text.
    
    Raw text to parse:
    {raw_text[:2000]}
    """

    # Query Llama-3 using updated model formatting
    llm_response = query_llm({
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.1
    })
    
    if llm_response is None:
        return []

    # Extract response string from standard JSON output
    if isinstance(llm_response, dict) and "choices" in llm_response:
        ai_output = llm_response["choices"][0]["message"]["content"]
    else:
        ai_output = str(llm_response)

    raw_response = ai_output.strip()

    # Robust parsing via Regex
    try:
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_response, re.DOTALL)
        if json_match:
            clean_json_text = json_match.group(0)
        else:
            clean_json_text = raw_response.replace("```json", "").replace("```", "").strip()

        return json.loads(clean_json_text)
    except json.JSONDecodeError as e:
        print(f"❌ Hugging Face parsing failed: {e}")
        print(f"Raw AI Output was:\n{raw_response}")
        return []

def run_scraper():
    print("🚀 Starting automated web scraper...")
    
    # Target Website: Your live repository source file
    url = url = "https://raw.githubusercontent.com/joshbuchea/HEAD/master/README.md"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to reach target site. Status code: {response.status_code}")
            return
            
        raw_web_text = response.text
        
        # Pass the dynamically pulled raw text to Hugging Face
        scraped_opportunities = get_ai_structured_opportunities(raw_web_text)
        
        if not scraped_opportunities:
            print("⚠️ No opportunities extracted by the AI.")
            return
            
        print(f"📦 Hugging Face successfully structured {len(scraped_opportunities)} opportunities!")
        print("Checking database for duplicates...")
        
        inserted_count = 0
        for opp in scraped_opportunities:
            title = opp.get("Title")

            # --- BACKUP SUBJECT GUARDRAILS ---
            subject = opp.get("Subject", "Interdisciplinary STEM")
            if isinstance(subject, list) and len(subject) > 0:
                subject = subject[0]
            elif isinstance(subject, str) and "," in subject:
                subject = subject.split(",")[0].strip()
            elif isinstance(subject, str) and " and " in subject:
                subject = subject.split(" and ")[0].strip()
            # ---------------------------------

            try:
                # 🔍 Supabase Duplication Checker
                existing = supabase.table("Opportunities").select("Title").eq("Title", title).execute()
                
                if len(existing.data) > 0:
                    print(f"⏭️ Skipping: '{title}' (Already exists in your Database)")
                    continue

                payload = {
                    "Title": title,
                    "Type": opp.get("Type"),
                    "Subject": subject,
                    "Tags": opp.get("Tags"),
                    "Deadline": opp.get("Deadline"),
                    "Link": opp.get("Link"),
                    "Description": opp.get("Description"),
                    "Is_Paid": opp.get("Is_Paid", False)
                }
                
                # Insert if unique
                supabase.table("Opportunities").insert(payload).execute()
                print(f"✅ AI-Tagged Insertion Successful: '{title}' | Subject: {subject} | Tags: {payload['Tags']}")
                inserted_count += 1
                
            except Exception as database_err:
                print(f"⚠️ Error processing database entry for '{title}': {database_err}")
                
        print(f"🎉 Scraping run finished! Added {inserted_count} new entries.")
        
    except Exception as e:
        print(f"❌ An error occurred while scraping: {e}")

if __name__ == "__main__":
    run_scraper()