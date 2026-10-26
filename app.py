import streamlit as st
from datetime import date
from src.database import supabase
from src.saved import parse_deadline

st.set_page_config(page_title="STEM Hub", page_icon="🚀", layout="wide")

st.title("STEM Hub")
st.subheader("Stop searching 50 websites. Find the STEM program that fits *you*.")
st.write(
    "Great STEM competitions, research programs and camps are scattered across the internet, "
    "and it's hard to know which ones fit your interests. STEM Hub collects them in one place, "
    "matches you to a field with a short quiz, and helps you track deadlines."
)

try:
    data = supabase.table("Opportunities").select("Title,Subject,Deadline").execute().data or []
except Exception:
    data = []

today = date.today()
upcoming = []
for o in data:
    d = parse_deadline(o.get("Deadline"))
    if d and d >= today:
        upcoming.append((d, o.get("Title")))
upcoming.sort()

c1, c2, c3 = st.columns(3)
c1.metric("Opportunities", len(data))
c2.metric("STEM fields covered", len({o.get("Subject") for o in data if o.get("Subject")}))
c3.metric("Upcoming deadlines", len(upcoming))

st.markdown("---")
b1, b2, b3 = st.columns(3)
b1.page_link("pages/2_Quiz.py", label="🧠 Take the Pathway Quiz", use_container_width=True)
b2.page_link("pages/1_Directory.py", label="🔍 Browse the Directory", use_container_width=True)
b3.page_link("pages/3_Dashboard.py", label="📋 My Dashboard", use_container_width=True)

if upcoming:
    st.markdown("### Closing soonest")
    for d, title in upcoming[:5]:
        st.write(f"**{title}** — {(d - today).days} days left ({d.strftime('%b %d, %Y')})")