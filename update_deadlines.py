import os
import re
import sys
import time
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database import supabase
from scraper import query_llm, fetch_source_text

MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
KEYWORDS = re.compile(
    r"deadline|due|apply by|applications? (?:open|close|due)|closes?|closing|rolling|"
    r"(?:" + MONTHS + r")\.?\s+\d{1,2}",
    re.IGNORECASE,
)


def deadline_snippet(text, limit=4000):
    """Keep only lines likely to mention a deadline, so the AI isn't flooded
    with a whole web page and the call stays cheap and focused."""
    hits = [ln.strip() for ln in text.splitlines() if ln.strip() and KEYWORDS.search(ln)]
    return "\n".join(hits)[:limit]


def ask_for_deadline(title, snippet):
    today = date.today().strftime("%B %d, %Y")
    prompt = f"""
Today's date is {today}.
Below are lines from the official web page for the program "{title}".
Find this program's APPLICATION DEADLINE.

STRICT RULES:
- Only use a date that is explicitly written in the text. Never guess or invent one.
- If an exact date is given, answer in MM-DD-YYYY format.
- If a month and day are given with no year, use the next occurrence of that date on or after today.
- If applications are rolling / accepted year-round, answer: Rolling
- If no clear application deadline appears, answer: TBD
- Answer with ONLY the value (for example 03-15-2027, Rolling, or TBD). No other words.

Text:
{snippet}
"""
    resp = query_llm({
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 20,
        "temperature": 0,
    })
    if not resp or "choices" not in resp:
        return None
    return resp["choices"][0]["message"]["content"].strip()


def clean_answer(answer):
    """Returns a safe value to store, or None to leave the row unchanged."""
    if not answer:
        return None
    if re.search(r"rolling", answer, re.IGNORECASE):
        return "Rolling"
    match = re.search(r"\b(\d{2})-(\d{2})-(\d{4})\b", answer)
    if not match:
        return None
    try:
        d = datetime.strptime(match.group(0), "%m-%d-%Y").date()
    except ValueError:
        return None
    if d < date.today() or d.year >= 2090:
        return None  # stale or placeholder date; don't store it
    return match.group(0)


def needs_deadline(value):
    v = (value or "").strip().lower()
    return v in ("", "tbd", "n/a") or "2099" in v


def run():
    rows = supabase.table("Opportunities").select("id,Title,Link,Deadline").execute().data or []
    todo = [r for r in rows if needs_deadline(r.get("Deadline")) and str(r.get("Link") or "").startswith("http")]
    print(f"🔎 {len(todo)} of {len(rows)} opportunities need a deadline. Checking each official page...\n")

    updated = 0
    for i, row in enumerate(todo, start=1):
        title = row["Title"]
        print(f"[{i}/{len(todo)}] {title}")
        text = fetch_source_text(row["Link"])
        if not text:
            print("   ⏭️ couldn't load the page, leaving as is")
            continue
        snippet = deadline_snippet(text)
        if not snippet:
            print("   ⏭️ no deadline-like text on the page")
            continue
        value = clean_answer(ask_for_deadline(title, snippet))
        if not value:
            print("   ⏭️ no clear deadline found")
            continue
        try:
            supabase.table("Opportunities").update({"Deadline": value}).eq("id", row["id"]).execute()
            print(f"   ✅ Deadline set to {value}")
            updated += 1
        except Exception as e:
            print(f"   ⚠️ database error: {e}")
        time.sleep(1)

    print(f"\n🎉 Done. Filled in {updated} deadlines.")


if __name__ == "__main__":
    run()