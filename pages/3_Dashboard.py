import streamlit as st
from datetime import date
from src.database import supabase
from src.saved import current_user, get_saved, remove, update_notes, parse_deadline

st.set_page_config(page_title="My Dashboard", page_icon="📋", layout="wide")

st.header("Your Personal STEM Dashboard")
st.write("Your saved opportunities, sorted by what's due soonest, with notes for each.")

user = current_user()
if not user:
    st.info("👈 Enter your name in the sidebar to see your saved opportunities.")
    st.stop()

saved = get_saved(user)
if not saved:
    st.info("Nothing saved yet. Open the Directory and tap **💾 Save to my dashboard** on anything interesting.")
    st.stop()

try:
    rows = supabase.table("Opportunities").select("*").in_("id", list(saved.keys())).execute().data or []
except Exception as e:
    st.error(f"Couldn't load your saved opportunities: {e}")
    st.stop()

today = date.today()
items = []
for opp in rows:
    d = parse_deadline(opp.get("Deadline"))
    days = (d - today).days if d else None
    items.append((opp, days))


def sort_key(item):
    days = item[1]
    if days is None:
        return (1, 0)          # undated (Rolling/TBD) in the middle
    if days < 0:
        return (2, -days)      # expired last
    return (0, days)           # upcoming first, soonest first


items.sort(key=sort_key)

upcoming = [d for _, d in items if d is not None and d >= 0]
due_soon = [d for d in upcoming if d <= 14]

c1, c2, c3 = st.columns(3)
c1.metric("Saved", len(items))
c2.metric("Due in 14 days", len(due_soon))
c3.metric("Next deadline", f"{min(upcoming)} days" if upcoming else "—")

st.markdown("---")


def status_label(days, deadline):
    if days is None:
        return f"{deadline or 'TBD'}"
    if days < 0:
        return "Deadline passed"
    if days == 0:
        return "Due today!"
    if days <= 7:
        return f"{days} days left"
    if days <= 30:
        return f"{days} days left"
    return f"{days} days left"


for opp, days in items:
    opp_id = opp.get("id")
    with st.container():
        left, right = st.columns([3, 1])
        left.subheader(opp.get("Title"))
        right.markdown(f"### {status_label(days, opp.get('Deadline'))}")

        st.write(f"{opp.get('Type')} | 📚 {opp.get('Subject')} | "
                 f"{'Paid' if opp.get('Is_Paid') else 'Free / Stipend'}")
        st.write(opp.get("Description"))
        st.markdown(f"[Visit Official Website]({opp.get('Link')})")

        notes = st.text_area(
            "Prep notes",
            value=saved.get(opp_id, ""),
            key=f"notes_{opp_id}",
            placeholder="Essay ideas, recommenders to ask, requirements...",
        )
        b1, b2, _ = st.columns([1, 1, 4])
        if b1.button("Save notes", key=f"sn_{opp_id}"):
            update_notes(user, opp_id, notes)
            st.toast("Notes saved ✅")
        if b2.button("Remove", key=f"rm_{opp_id}"):
            remove(user, opp_id)
            st.rerun()
        st.markdown("---")