import streamlit as st
from datetime import date
from src.database import supabase
from src.saved import current_user, get_saved, save, remove, parse_deadline

st.set_page_config(page_title="STEM Opportunities Directory", page_icon="🔍", layout="wide")

st.header("🔍 Discover STEM Opportunities")
st.write("Filter through curated competitions, internships, and camps.")

# --- USER + SAVED LIST (for the Save buttons) ---
user = current_user()
saved_ids = set(get_saved(user).keys()) if user else set()

# --- STEP 1: FETCH ALL DATA ---
try:
    response = supabase.table("Opportunities").select("*").execute()
    all_opportunities = response.data if response.data else []
except Exception as e:
    st.error(f"Error connecting to database: {e}")
    all_opportunities = []

# --- STEP 2: EXTRACT UNIQUE OPTIONS DYNAMICALLY ---
dynamic_types = sorted(set(opp.get("Type") for opp in all_opportunities if opp.get("Type")))
dynamic_subjects = sorted(set(opp.get("Subject") for opp in all_opportunities if opp.get("Subject")))

all_tags = []
for opp in all_opportunities:
    tags = opp.get("Tags")
    if isinstance(tags, list):
        all_tags.extend(tags)
unique_tags = sorted(set(all_tags))

# --- STEP 3: CREATE THE FILTERS ---
search_text = st.text_input("🔎 Search by keyword", placeholder="e.g. robotics, genetics, NASA...")

col1, col2, col3 = st.columns(3)

with col1:
    selected_types = st.multiselect(
        "Filter by Opportunity Type:",
        options=dynamic_types,
        placeholder="All Types",
    )

with col2:
    selected_subjects = st.multiselect(
        "Filter by Subject Category:",
        options=dynamic_subjects,
        placeholder="All Subjects",
    )

with col3:
    selected_tags = st.multiselect(
        "Filter by AI Topic Tags:",
        options=unique_tags,
        placeholder="All Topic Tags",
    )

# --- ADVANCED FILTERS ---
st.markdown("### ⚙️ Advanced Filters")
col_cost, col_date = st.columns(2)

with col_cost:
    cost_filter = st.radio(
        "Program Cost:",
        options=["All", "Free / Fully Funded Only", "Paid Programs Only"],
        horizontal=True,
    )

with col_date:
    # Off by default. When checked, hides opportunities whose deadline has
    # already passed. Vague deadlines like "Rolling" or "TBD" stay visible.
    hide_expired = st.checkbox("Hide expired deadlines", value=False)

st.markdown("---")

# --- STEP 4: APPLY STRICT "AND" FILTERING LOGIC ---
filtered_opportunities = []
today = date.today()
query = search_text.strip().lower()

for opp in all_opportunities:
    # 1. Type & Subject match
    type_match = not selected_types or opp.get("Type") in selected_types
    subject_match = not selected_subjects or opp.get("Subject") in selected_subjects

    # 2. Tags match
    opp_tags = opp.get("Tags") if isinstance(opp.get("Tags"), list) else []
    tags_match = not selected_tags or all(tag in opp_tags for tag in selected_tags)

    # 3. Cost match (robust for booleans, strings, or missing values)
    is_paid_raw = opp.get("Is_Paid")
    if is_paid_raw is None:
        is_paid_bool = False
    elif isinstance(is_paid_raw, str):
        is_paid_bool = is_paid_raw.strip().lower() in ["true", "1", "yes"]
    else:
        is_paid_bool = bool(is_paid_raw)

    if cost_filter == "Free / Fully Funded Only":
        cost_match = not is_paid_bool
    elif cost_filter == "Paid Programs Only":
        cost_match = is_paid_bool
    else:
        cost_match = True

    # 4. Deadline match
    deadline_match = True
    if hide_expired:
        parsed = parse_deadline(opp.get("Deadline"))
        if parsed is not None and parsed < today:
            deadline_match = False

    # 5. Keyword search across title, description, subject and tags
    if query:
        haystack = " ".join([
            str(opp.get("Title") or ""),
            str(opp.get("Description") or ""),
            str(opp.get("Subject") or ""),
            " ".join(opp_tags),
        ]).lower()
        search_match = query in haystack
    else:
        search_match = True

    if type_match and subject_match and tags_match and cost_match and deadline_match and search_match:
        filtered_opportunities.append(opp)

# --- STEP 5: DISPLAY THE RESULTS ---
if not filtered_opportunities:
    st.info("No opportunities match your current filter selections. Try broadening your search!")
else:
    st.write(f"Showing **{len(filtered_opportunities)}** of **{len(all_opportunities)}** opportunities:")

    for opp in filtered_opportunities:
        opp_id = opp.get("id")
        with st.container():
            st.subheader(f"{opp.get('Title')}")

            # Pricing badge
            is_paid = opp.get("Is_Paid", False)
            cost_badge = "💰 Paid / Has Fee" if is_paid else "🎁 Free / Stipend"

            # Metadata rows
            st.write(f"💼 **Type:** {opp.get('Type')} | 📚 **Subject:** {opp.get('Subject')} | {cost_badge}")

            deadline = opp.get("Deadline") if opp.get("Deadline") else "No deadline specified"
            parsed = parse_deadline(opp.get("Deadline"))
            if parsed is not None:
                days_left = (parsed - today).days
                if days_left < 0:
                    deadline += "  ⛔ passed"
                elif days_left <= 14:
                    deadline += f"  🔥 {days_left} days left"
            st.write(f"🗓️ **Deadline:** {deadline}")

            tags_list = opp.get("Tags") if isinstance(opp.get("Tags"), list) else []
            st.write(f"🏷️ **Tags:** {', '.join(f'`{t}`' for t in tags_list) if tags_list else 'None'}")

            # Description & link
            st.write(opp.get("Description"))
            st.markdown(f"[Visit Official Website]({opp.get('Link')})")

            # Save / unsave button
            if not user:
                st.caption("👈 Enter your name in the sidebar to save this.")
            elif opp_id in saved_ids:
                if st.button("✅ Saved (click to remove)", key=f"rm_{opp_id}"):
                    remove(user, opp_id)
                    st.rerun()
            else:
                if st.button("💾 Save to my dashboard", key=f"save_{opp_id}"):
                    save(user, opp_id)
                    st.rerun()

            st.markdown("---")