import sys
import os
import requests
import json
import re
from bs4 import BeautifulSoup
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

# Multiple sources across different STEM subjects, not just one
# open-source/software list. Each is fetched, cleaned, and parsed the same
# way. Add more URLs here any time you find a good list to pull from.
SOURCE_URLS = [
    "https://raw.githubusercontent.com/Astroxphiliauxx/open-source-guide-2026/main/README.md",
    "https://www.collegetransitions.com/blog/research-opportunities-for-high-school-students/",
    "https://empowerly.com/applications/research-projects/research-opportunities-high-school-students/",
    "https://www.cosmic.nyc/blog/master-list-of-stem-summer-programs-for-high-school-students",
]

# Eligibility categories that don't fit a high-school directory and should
# be filtered out automatically rather than inserted.
NON_HS_ELIGIBILITY = {"College/University", "18+ / Professional"}


def fetch_source_text(url):
    """Fetches a source URL and returns clean, readable text. Handles both
    raw markdown (like a GitHub README) and regular HTML blog pages."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException as e:
        print(f"❌ Failed to reach {url}: {e}")
        return None

    if resp.status_code != 200:
        print(f"❌ Failed to reach {url}. Status code: {resp.status_code}")
        return None

    content = resp.text
    sniff = content[:1000].lower()
    if "<html" in sniff or "<!doctype" in sniff:
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "svg"]):
            tag.decompose()
        return soup.get_text(separator="\n")

    return content


def query_llm(payload):
    """Sends prompt request directly to Hugging Face API"""
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    if response.status_code != 200:
        print(f"⚠️ Hugging Face API returned status code {response.status_code}")
        print(f"Response: {response.text}")
        return None
    return response.json()

def get_ai_structured_opportunities(raw_text):
    """Feeds raw text to Llama-3 and structures current 2026 and 2027 opportunities"""
    print("🧠 Asking Hugging Face (Llama-3) to parse structured data...")
    
    prompt = f"""
    You are an expert data organizer for a High School STEM Directory website.
    I am giving you raw text scraped from a website listing specific pre-college programs, internships, and STEM opportunities.

    CRITICAL RULES:
    1. DO NOT extract category headers, section titles, navigation links, or ads.
    2. Extract up to 20 ACTUAL, distinct named opportunities/programs.
    3. EVERY program MUST have a completely UNIQUE, custom description. DO NOT repeat or reuse descriptions across items.
    4. Only extract real, specific, named programs. Skip generic mentions ("many universities offer summer programs") with no actual name.

    For each opportunity, extract:
    - Title: The official, specific name of the program.
    - Type: Choose exactly one from ["Competitions/Hackathons", "Research & Fellowships", "Internships", "Summer Camps", "Scholarships"].
    - Subject: Choose EXACTLY ONE from: ["Computer Science", "Engineering", "Biology", "Chemistry", "Physics", "Mathematics", "Earth & Environmental Science", "Interdisciplinary STEM"].
    - Tags: A list of 2 to 4 specific sub-topic tags (e.g., ["Coding", "AI", "Robotics"]).
    - Eligibility: Choose EXACTLY ONE from ["High School (9-12)", "College/University", "18+ / Professional", "All Ages / Open to Everyone"], based on the stated age/grade requirements. If a program explicitly requires being a university student, graduate, or professional (not a high schooler), mark it "College/University" or "18+ / Professional" accordingly. If it's explicitly open to high schoolers or doesn't specify an age restriction, use "High School (9-12)" or "All Ages / Open to Everyone".
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


def chunk_text(text, chunk_size=8000):
    """Splits text into chunks on line boundaries so we never cut an entry
    mid-way, and so a long source doc isn't truncated down to its first
    slice."""
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) > chunk_size and current:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)
    return chunks


def run_scraper():
    print("🚀 Starting Automated Web Scraper...")

    scraped_opportunities = []
    seen_titles = set()  # deduped across ALL sources, not just within one

    for source_url in SOURCE_URLS:
        print(f"\n🌐 Fetching source: {source_url}")
        raw_web_text = fetch_source_text(source_url)
        if not raw_web_text:
            continue

        chunks = chunk_text(raw_web_text)
        print(f"📄 Split into {len(chunks)} chunk(s) for parsing...")

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

    print(f"\n📦 Hugging Face successfully structured {len(scraped_opportunities)} opportunities total!")
    print("Checking database for duplicates and high-school eligibility...")

    inserted_count = 0
    skipped_ineligible = 0

    for opp in scraped_opportunities:
        title = opp.get("Title")
        if not title:
            continue

        # --- ELIGIBILITY GUARDRAIL ---
        # This directory is for high schoolers. Skip anything explicitly
        # flagged as college/university or 18+/professional only.
        eligibility = opp.get("Eligibility", "All Ages / Open to Everyone")
        if isinstance(eligibility, list) and eligibility:
            eligibility = eligibility[0]
        if eligibility in NON_HS_ELIGIBILITY:
            print(f"🚫 Skipping (not high-school-eligible): '{title}' — {eligibility}")
            skipped_ineligible += 1
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
            print(f"✅ Insertion Successful: '{title}' | Subject: {subject} | Deadline: {payload['Deadline']}")
            inserted_count += 1

        except Exception as database_err:
            print(f"⚠️ Error processing database entry for '{title}': {database_err}")

    print(f"\n🎉 Scraping run finished! Added {inserted_count} new entries. "
          f"Skipped {skipped_ineligible} as not high-school-eligible.")

if __name__ == "__main__":
    run_scraper()