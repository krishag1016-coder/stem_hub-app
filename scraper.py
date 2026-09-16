import sys
import os
import requests
import json
import re
from dotenv import load_dotenv

# Load API Keys from .env
load_dotenv()

# Ensure Python can find database configuration files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.database import supabase

# --- CONFIGURATION ---
HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_HEADERS = {
    "Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}",
    "Content-Type": "application/json"
}

def query_llm(payload):
    """Sends prompt request directly to Hugging Face API"""
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Hugging Face API returned status code {response.status_code}")
        print(f"Response: {response.text}")
        return None
    return response.json()

def get_ai_structured_opportunities(raw_text):
    """Feeds raw markdown text to Llama-3 and structures current 2026 and 2027 opportunities"""
    print("🧠 Asking Hugging Face (Llama-3) to parse structured data...")
    
    prompt = f"""
    You are an expert data organizer for a High School STEM Directory website.
    I am giving you raw text scraped from a website listing specific pre-college programs, internships, and STEM opportunities.

    CRITICAL RULES:
    1. DO NOT extract category headers or section titles.
    2. Extract up to 20 ACTUAL, distinct named opportunities/programs.
    3. EVERY program MUST have a completely UNIQUE, custom description. DO NOT repeat or reuse descriptions across items.

    For each opportunity, extract:
    - Title: The official, specific name of the program.
    - Type: Choose exactly one from ["Competitions/Hackathons", "Research & Fellowships", "Internships", "Summer Camps", "Scholarships"].
    - Subject: Choose EXACTLY ONE from: ["Computer Science", "Engineering", "Biology", "Chemistry", "Physics", "Mathematics", "Earth & Environmental Science", "Interdisciplinary STEM"].
    - Tags: A list of 2 to 4 specific sub-topic tags (e.g., ["Coding", "AI", "Robotics"]).
    - Deadline: Extract the deadline date:
        a) If a date is given (e.g., "March 31st", "05/01/2026", "May 1"), format it strictly as "MM-DD-YYYY" (use 2099 if year is unspecified).
        b) If vague or rolling (e.g., "Rolling", "Spring 2026"), output that exact short phrase.
        c) If no deadline is stated, output "TBD".
    - Link: The direct website URL for the opportunity. If missing, output "N/A".
    - Description: A clear, compelling 1-2 sentence summary SPECIFIC to what this exact program offers. Do not copy description text from other programs.
    - Is_Paid: Set to true if there is a tuition/application fee. Set to false if free, fully funded, or offers a stipend.

    Return ONLY a raw JSON array of objects. No markdown formatting, no code blocks (do not use ```json), no trailing text.

    Raw text to parse:
    {raw_text}
    """

    llm_response = query_llm({
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3500,
        "temperature": 0.1
    })
    
    if llm_response is None:
        return []

    if isinstance(llm_response, dict) and "choices" in llm_response:
        ai_output = llm_response["choices"][0]["message"]["content"]
    else:
        ai_output = str(llm_response)

    raw_response = ai_output.strip()

    try:
        json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_response, re.DOTALL)
        if json_match:
            clean_json_text = json_match.group(0)
        else:
            clean_json_text = raw_response.replace("```json", "").replace("```", "").strip()

        return json.loads(clean_json_text)
    except json.JSONDecodeError as e:
        print(f"❌ Hugging Face JSON parsing failed: {e}")
        return []

def run_scraper():
    print("🚀 Starting Automated Web Scraper...")
    
    # Target directory URL: Dedicated High School Pre-College Opportunity List
    index_url = "https://raw.githubusercontent.com/Astroxphiliauxx/open-source-guide-2026/main/README.md"
    
    try:
        response = requests.get(index_url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to reach target site. Status code: {response.status_code}")
            return
            
        raw_web_text = response.text
        
        # Send raw summary text directly to Hugging Face
        raw_web_text = response.text

        CHUNK_SIZE = 8000
        lines = raw_web_text.splitlines(keepends=True)
        chunks, current = [], ""
        for line in lines:
            if len(current) + len(line) > CHUNK_SIZE and current:
                chunks.append(current)
                current = ""
            current += line
        if current:
            chunks.append(current)

        print(f"📄 Source document split into {len(chunks)} chunk(s) for parsing...")

        scraped_opportunities = []
        seen_titles = set()
        for i, chunk in enumerate(chunks, start=1):
            print(f"🧩 Parsing chunk {i}/{len(chunks)}...")
            chunk_results = get_ai_structured_opportunities(chunk)
            for opp in chunk_results:
                title_key = str(opp.get("Title", "")).strip().lower()
                if not title_key or title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                scraped_opportunities.append(opp)

        if not scraped_opportunities:
            print("⚠️ No opportunities were extracted by the AI.")
            return

        print(f"📦 Hugging Face successfully structured {len(scraped_opportunities)} opportunities!")
        
        inserted_count = 0
        for opp in scraped_opportunities:
            title = opp.get("Title")
            if not title:
                continue

            # --- BACKUP SUBJECT GUARDRAILS ---
            subject = opp.get("Subject", "Interdisciplinary STEM")
            if isinstance(subject, list) and len(subject) > 0:
                subject = subject[0]
            elif isinstance(subject, str) and "," in subject:
                subject = subject.split(",")[0].strip()
            elif isinstance(subject, str) and " and " in subject:
                subject = subject.split(" and ")[0].strip()
            # ---------------------------------

            # Ensure Is_Paid is strictly boolean
            raw_is_paid = opp.get("Is_Paid")
            is_paid_bool = True if raw_is_paid is True else False

            try:
                # Duplication Check
                existing = supabase.table("Opportunities").select("Title").eq("Title", title).execute()
                if len(existing.data) > 0:
                    print(f"⏭️ Skipping: '{title}' (Already exists in database)")
                    continue

                payload = {
                    "Title": title,
                    "Type": opp.get("Type", "Competitions/Hackathons"),
                    "Subject": subject,
                    "Tags": opp.get("Tags", []),
                    "Deadline": str(opp.get("Deadline", "TBD")),
                    "Link": opp.get("Link", "N/A"),
                    "Description": opp.get("Description", ""),
                    "Is_Paid": is_paid_bool
                }
                
                # Insert into Supabase
                supabase.table("Opportunities").insert(payload).execute()
                print(f"✅ Insertion Successful: '{title}' | Deadline: {payload['Deadline']}")
                inserted_count += 1
                
            except Exception as database_err:
                print(f"⚠️ Error processing database entry for '{title}': {database_err}")
                
        print(f"\n🎉 Scraping run finished! Added {inserted_count} new entries.")
        
    except Exception as e:
        print(f"❌ An error occurred while scraping: {e}")

if __name__ == "__main__":
    run_scraper()