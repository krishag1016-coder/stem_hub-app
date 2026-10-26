import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Make the project root available when this file runs directly.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.database import supabase

load_dotenv()

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

SOURCE_URLS = [
    "https://raw.githubusercontent.com/Astroxphiliauxx/open-source-guide-2026/main/README.md",
    "https://www.collegetransitions.com/blog/research-opportunities-for-high-school-students/",
    "https://empowerly.com/applications/research-projects/research-opportunities-high-school-students/",
    "https://www.cosmic.nyc/blog/master-list-of-stem-summer-programs-for-high-school-students",
]

ALLOWED_TYPES = {
    "Competitions/Hackathons",
    "Research & Fellowships",
    "Internships",
    "Summer Camps",
    "Scholarships",
}

ALLOWED_SUBJECTS = {
    "Computer Science",
    "Engineering",
    "Biology",
    "Chemistry",
    "Physics",
    "Mathematics",
    "Earth & Environmental Science",
    "Interdisciplinary STEM",
}

NON_HS_ELIGIBILITY = {
    "College/University",
    "18+ / Professional",
}


def fetch_source_text(url):
    """Download a page and return readable text."""
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 StemHub/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Could not fetch {url}: {exc}")
        return None

    content = response.text
    start = content[:1000].lower()

    if "<html" in start or "<!doctype" in start:
        soup = BeautifulSoup(content, "html.parser")

        for element in soup(
            ["script", "style", "nav", "footer", "header", "svg", "noscript"]
        ):
            element.decompose()

        return soup.get_text(separator="\n", strip=True)

    return content


def chunk_text(text, chunk_size=8000):
    """Split long text into manageable chunks."""
    chunks = []
    current = []

    for line in text.splitlines():
        if len(line) > chunk_size:
            if current:
                chunks.append("\n".join(current))
                current = []

            chunks.extend(
                line[i:i + chunk_size]
                for i in range(0, len(line), chunk_size)
            )
            continue

        if sum(len(item) + 1 for item in current) + len(line) + 1 > chunk_size:
            if current:
                chunks.append("\n".join(current))
            current = []

        current.append(line)

    if current:
        chunks.append("\n".join(current))

    return chunks


def query_llm(prompt):
    """Send a request to Hugging Face and return the model's text."""
    api_key = os.getenv("HUGGINGFACE_API_KEY")

    if not api_key:
        print("HUGGINGFACE_API_KEY is missing from your .env file.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": HF_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3500,
        "temperature": 0.1,
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        print(f"Hugging Face request failed: {exc}")
        return None
    except ValueError:
        print("Hugging Face returned invalid JSON.")
        return None

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(f"Unexpected Hugging Face response: {data}")
        return None


def extract_json_array(text):
    """Extract a JSON array, even if the model adds code fences."""
    if not text:
        return []

    cleaned = text.strip()
    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        pass

    start = cleaned.find("[")
    end = cleaned.rfind("]")

    if start == -1 or end <= start:
        print("The model response did not contain a JSON array.")
        return []

    try:
        result = json.loads(cleaned[start:end + 1])
        return result if isinstance(result, list) else []
    except json.JSONDecodeError as exc:
        print(f"Could not parse the model's JSON response: {exc}")
        return []


def get_ai_structured_opportunities(raw_text):
    """Extract named opportunities from source text."""
    prompt = f"""
You organize information for StemHub, a directory for high-school students.

Extract only specific, named programs mentioned in the source text.
Do not invent programs, dates, links, eligibility, costs, or program details.
Do not treat a page's publication date as an application deadline.

Return only a JSON array. Each object must contain:

- Title: official program name.
- Type: exactly one of {sorted(ALLOWED_TYPES)}.
- Subject: exactly one of {sorted(ALLOWED_SUBJECTS)}.
- Tags: an array of 2 to 4 relevant short tags.
- Eligibility: use "High School (9-12)", "College/University",
  "18+ / Professional", or "All Ages / Open to Everyone" only when supported.
  Otherwise use "Eligibility not confirmed".
- Deadline: if a complete date is provided, use YYYY-MM-DD.
  If the year is missing, preserve the date and say "(year not listed)".
  Do not guess the year. Use "Rolling" for rolling deadlines and "TBD"
  if no deadline is stated.
- Link: direct program URL if present, otherwise "N/A".
- Description: one or two factual sentences about this specific program.
- Is_Paid: true if a fee is explicitly stated; false if it is explicitly free,
  fully funded, or offers a stipend. Otherwise use null.

Extract up to 15 opportunities from this text. Skip headings, ads, and
generic mentions. Do not include text outside the JSON array.

SOURCE TEXT:
{raw_text}
"""

    response = query_llm(prompt)
    opportunities = extract_json_array(response)

    return [
        item for item in opportunities
        if isinstance(item, dict)
    ]


def clean_text(value, fallback=""):
    if value is None:
        return fallback

    value = str(value).strip()
    return value if value else fallback


def normalize_tags(value):
    if isinstance(value, str):
        value = value.split(",")

    if not isinstance(value, list):
        return []

    result = []

    for item in value:
        tag = clean_text(item)

        if tag and tag not in result:
            result.append(tag)

    return result[:4]


def normalize_subject(value):
    if isinstance(value, list):
        value = value[0] if value else ""

    value = clean_text(value)

    if value in ALLOWED_SUBJECTS:
        return value

    return "Interdisciplinary STEM"


def normalize_type(value):
    value = clean_text(value)

    if value in ALLOWED_TYPES:
        return value

    return "Competitions/Hackathons"


def normalize_paid(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value = value.strip().casefold()

        if value in {"true", "yes", "1"}:
            return True

        if value in {"false", "no", "0"}:
            return False

    # Keep unknown cost information unknown.
    return None


def is_duplicate(title):
    """Check existing titles without relying on capitalization."""
    try:
        response = (
            supabase.table("Opportunities")
            .select("Title")
            .execute()
        )

        wanted = title.casefold()

        return any(
            clean_text(row.get("Title")).casefold() == wanted
            for row in (response.data or [])
        )

    except Exception as exc:
        # Don't insert a record if the duplicate check failed.
        print(f"Could not check for duplicate '{title}': {exc}")
        return True


def run_scraper():
    print("Starting StemHub's opportunity import.")

    scraped = []
    seen_titles = set()

    for source_url in SOURCE_URLS:
        print(f"\nReading source: {source_url}")

        source_text = fetch_source_text(source_url)

        if not source_text:
            continue

        chunks = chunk_text(source_text)
        print(f"Found {len(chunks)} text section(s).")

        for index, chunk in enumerate(chunks, start=1):
            print(f"Processing section {index}/{len(chunks)}...")

            for opportunity in get_ai_structured_opportunities(chunk):
                title = clean_text(opportunity.get("Title"))

                if not title:
                    continue

                title_key = title.casefold()

                if title_key in seen_titles:
                    continue

                seen_titles.add(title_key)
                scraped.append(opportunity)

    if not scraped:
        print("No opportunities were extracted. Nothing was added.")
        return

    added = 0
    skipped_ineligible = 0
    skipped_duplicates = 0

    for opportunity in scraped:
        title = clean_text(opportunity.get("Title"))

        eligibility = clean_text(
            opportunity.get("Eligibility"),
            "Eligibility not confirmed",
        )

        if eligibility in NON_HS_ELIGIBILITY:
            print(f"Skipped {title}: not intended for high-school students.")
            skipped_ineligible += 1
            continue

        if is_duplicate(title):
            print(f"Skipped {title}: duplicate or database check failed.")
            skipped_duplicates += 1
            continue

        deadline = clean_text(opportunity.get("Deadline"), "TBD")
        link = clean_text(opportunity.get("Link"), "N/A")

        if link.casefold() in {"none", "null"}:
            link = "N/A"

        payload = {
            "Title": title,
            "Type": normalize_type(opportunity.get("Type")),
            "Subject": normalize_subject(opportunity.get("Subject")),
            "Tags": normalize_tags(opportunity.get("Tags")),
            "Deadline": deadline,
            "Link": link,
            "Description": clean_text(opportunity.get("Description")),
            "Is_Paid": normalize_paid(opportunity.get("Is_Paid")),
        }

        try:
            (
                supabase.table("Opportunities")
                .insert(payload)
                .execute()
            )

            print(f"Added: {title} | Deadline: {deadline}")
            added += 1

        except Exception as exc:
            print(f"Could not add '{title}': {exc}")

    print(
        "\nImport finished. "
        f"Added: {added}; "
        f"skipped as university/adult-only: {skipped_ineligible}; "
        f"skipped as duplicate or unchecked: {skipped_duplicates}."
    )

    print(
        "Check each new opportunity against its official website before "
        "relying on its deadline, eligibility, or cost."
    )


if __name__ == "__main__":
    run_scraper()