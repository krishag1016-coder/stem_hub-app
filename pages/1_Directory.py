import streamlit as st
from src.database import supabase
from datetime import datetime, date

st.set_page_config(page_title="STEM Opportunities Directory", page_icon="🔍", layout="wide")

st.header("🔍 Discover STEM Opportunities")
st.write("Filter through curated competitions, internships, and camps.")

# --- STEP 1: FETCH ALL DATA ---
try:
    response = supabase.table("Opportunities").select("*").execute()
    all_opportunities = response.data if response.data else []
except Exception as e:
    st.error(f"Error connecting to database: {e}")
    all_opportunities = []

# --- STEP 2: EXTRACT UNIQUE OPTIONS DYNAMICALLY ---
dynamic_types = sorted(list(set(opp.get("Type") for opp in all_opportunities if opp.get("Type"))))
dynamic_subjects = sorted(list(set(opp.get("Subject") for opp in all_opportunities if opp.get("Subject"))))

all_tags = []
for opp in all_opportunities:
    tags = opp.get("Tags")
    if isinstance(tags, list):
        all_tags.extend(tags)
unique_tags = sorted(list(set(all_tags)))

# --- STEP 3: CREATE THE FILTERS ---
col1, col2, col3 = st.columns(3)

with col1:
    selected_types = st.multiselect(
        "Filter by Opportunity Type:", 
        options=dynamic_types,
        placeholder="All Types"
    )

with col2:
    selected_subjects = st.multiselect(
        "Filter by Subject Category:", 
        options=dynamic_subjects,
        placeholder="All Subjects"
    )

with col3:
    selected_tags = st.multiselect(
        "Filter by AI Topic Tags:", 
        options=unique_tags,
        placeholder="All Topic Tags"
    )

# --- ADVANCED FILTERS ---
st.markdown("### ⚙️ Advanced Filters")
col_cost, col_date = st.columns(2)

with col_cost:
    cost_filter = st.radio(
        "Program Cost:",
        options=["All", "Free / Fully Funded Only", "Paid Programs Only"],
        horizontal=True
    )

with col_date:
    # This checkbox is off by default, displaying everything.
    # When checked, it removes expired or unparseable deadlines.
    hide_expired_or_invalid = st.checkbox("Hide expired or invalid deadlines", value=False)

st.markdown("---")

# --- STEP 4: APPLY STRICT "AND" FILTERING LOGIC ---
filtered_opportunities = []
today = date.today()

for opp in all_opportunities:
    # 1. Type & Subject match
    type_match = not selected_types or opp.get("Type") in selected_types
    subject_match = not selected_subjects or opp.get("Subject") in selected_subjects
    
    # 2. Tags match
    opp_tags = opp.get("Tags") if isinstance(opp.get("Tags"), list) else []
    tags_match = not selected_tags or all(tag in opp_tags for tag in selected_tags)
    
    # 3. Cost Match (Robust comparison for Python Booleans, Strings, or missing fields)
    is_paid_raw = opp.get("Is_Paid")
    
    # Standardize the database value to a true/false Python boolean
    if is_paid_raw is None:
        is_paid_bool = False  # Default to Free if blank
    elif isinstance(is_paid_raw, str):
        is_paid_bool = is_paid_raw.strip().lower() in ["true", "1", "yes"]
    else:
        is_paid_bool = bool(is_paid_raw)

    # Compare with user's radio button selection
    if cost_filter == "Free / Fully Funded Only":
        cost_match = (is_paid_bool is False)
    elif cost_filter == "Paid Programs Only":
        cost_match = (is_paid_bool is True)
    else:
        cost_match = True  # "All" selected, so always match

    # 4. Smart Deadline Match
    deadline_str = opp.get("Deadline")
    deadline_match = True  # Keep visible by default!
    
    if hide_expired_or_invalid:
        if not deadline_str:
            deadline_match = False
        else:
            try:
                deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                if deadline_date < today:
                    deadline_match = False
            except ValueError:
                # Hide if format doesn't match YYYY-MM-DD
                deadline_match = False

    # Append only if the opportunity matches ALL active criteria
    if type_match and subject_match and tags_match and cost_match and deadline_match:
        filtered_opportunities.append(opp)

# --- STEP 5: DISPLAY THE RESULTS ---
if not filtered_opportunities:
    st.info("No opportunities match your current filter selections. Try broadening your search!")
else:
    st.write(f"Showing **{len(filtered_opportunities)}** of **{len(all_opportunities)}** opportunities:")
    
    for opp in filtered_opportunities:
        with st.container():
            opportunity_id = opp.get('id', 'N/A')
            st.subheader(f"#{opportunity_id} | {opp.get('Title')}")
            
            # Pricing indicator badge
            is_paid = opp.get("Is_Paid", False)
            cost_badge = "💰 Paid / Has Fee" if is_paid else "🎁 Free / Stipend"
            
            # Metadata row
            st.write(f"💼 **Type:** {opp.get('Type')} | 📚 **Subject:** {opp.get('Subject')} | {cost_badge}")
            st.write(f"🗓️ **Deadline:** {opp.get('Deadline') if opp.get('Deadline') else 'No deadline specified'}")
            
            # Render tags in pretty markdown code snippets
            tags_list = opp.get('Tags', [])
            st.write(f"🏷️ **Tags:** {', '.join([f'`{t}`' for t in tags_list]) if tags_list else 'None'}")
            
            # Description & URL
            st.write(opp.get('Description'))
            st.markdown(f"[Visit Official Website]({opp.get('Link')})")
            st.markdown("---")