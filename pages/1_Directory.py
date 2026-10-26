import streamlit as st
from datetime import date
from src.database import supabase
from src.saved import current_user, get_saved, save, remove, parse_deadline


st.set_page_config(
    page_title="StemHub | Discover Opportunities",
    layout="wide",
)

st.header("Find your next STEM opportunity")
st.write(
    "Explore competitions, summer programs, internships, and research "
    "opportunities. Use the filters to find ones that fit your interests."
)

# Get the current user's saved opportunities.
user = current_user()
saved_ids = set(get_saved(user).keys()) if user else set()


# Load opportunities from the database.
try:
    response = supabase.table("Opportunities").select("*").execute()
    all_opportunities = response.data or []
except Exception:
    st.error(
        "We couldn't load opportunities right now. "
        "Please try again in a little while."
    )
    all_opportunities = []


# Create filter options from the available data.
dynamic_types = sorted({
    str(opp["Type"])
    for opp in all_opportunities
    if opp.get("Type")
})

dynamic_subjects = sorted({
    str(opp["Subject"])
    for opp in all_opportunities
    if opp.get("Subject")
})

all_tags = []
for opp in all_opportunities:
    tags = opp.get("Tags")
    if isinstance(tags, list):
        all_tags.extend(str(tag) for tag in tags if tag)

unique_tags = sorted(set(all_tags))


# Let users search and filter the directory.
search_text = st.text_input(
    "Search opportunities",
    placeholder="Try robotics, biology, coding, or NASA",
)

col1, col2, col3 = st.columns(3)

with col1:
    selected_types = st.multiselect(
        "Opportunity type",
        options=dynamic_types,
        placeholder="All types",
    )

with col2:
    selected_subjects = st.multiselect(
        "Subject",
        options=dynamic_subjects,
        placeholder="All subjects",
    )

with col3:
    selected_tags = st.multiselect(
        "Topics and skills",
        options=unique_tags,
        placeholder="All topics",
    )


st.markdown("### More filters")

col_cost, col_deadline = st.columns(2)

with col_cost:
    cost_filter = st.radio(
        "Program cost",
        options=[
            "Any cost",
            "Free or fully funded",
            "Paid programs",
        ],
        horizontal=True,
    )

with col_deadline:
    hide_expired = st.checkbox(
        "Hide past deadlines",
        value=False,
    )

st.divider()


# Convert different database formats into a consistent cost value.
def get_paid_status(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)

    if isinstance(value, str):
        value = value.strip().casefold()

        if value in {"true", "1", "yes"}:
            return True
        if value in {"false", "0", "no"}:
            return False

    return None


# Keep opportunities that match all selected filters.
today = date.today()
query = search_text.strip().casefold()
filtered_opportunities = []

for opp in all_opportunities:
    type_match = (
        not selected_types
        or opp.get("Type") in selected_types
    )

    subject_match = (
        not selected_subjects
        or opp.get("Subject") in selected_subjects
    )

    tags = opp.get("Tags")
    if not isinstance(tags, list):
        tags = []

    tags = [str(tag) for tag in tags if tag]

    # Every selected topic must match.
    tags_match = (
        not selected_tags
        or all(tag in tags for tag in selected_tags)
    )

    # Apply the cost filter without treating unknown costs as free.
    is_paid = get_paid_status(opp.get("Is_Paid"))

    if cost_filter == "Free or fully funded":
        cost_match = is_paid is False
    elif cost_filter == "Paid programs":
        cost_match = is_paid is True
    else:
        cost_match = True

    # Hide past deadlines when requested. Unrecognized dates stay visible.
    parsed_deadline = parse_deadline(opp.get("Deadline"))

    deadline_match = not (
        hide_expired
        and parsed_deadline is not None
        and parsed_deadline < today
    )

    # Search the opportunity's title, description, subject, and tags.
    searchable_text = " ".join([
        str(opp.get("Title") or ""),
        str(opp.get("Description") or ""),
        str(opp.get("Subject") or ""),
        " ".join(tags),
    ]).casefold()

    search_match = not query or query in searchable_text

    if (
        type_match
        and subject_match
        and tags_match
        and cost_match
        and deadline_match
        and search_match
    ):
        filtered_opportunities.append(opp)


# Display the matching opportunities.
if not filtered_opportunities:
    st.info(
        "No opportunities match those filters. "
        "Try removing a filter or changing your search."
    )
else:
    st.write(
        f"Showing **{len(filtered_opportunities)}** of "
        f"**{len(all_opportunities)}** opportunities."
    )

    for opp in filtered_opportunities:
        opp_id = opp.get("id")
        title = opp.get("Title") or "Untitled opportunity"

        with st.container():
            st.subheader(title)

            opportunity_type = opp.get("Type") or "Type not listed"
            subject = opp.get("Subject") or "Subject not listed"
            is_paid = get_paid_status(opp.get("Is_Paid"))

            if is_paid is True:
                cost_label = "Paid"
            elif is_paid is False:
                cost_label = "Free / fully funded"
            else:
                cost_label = "Cost not listed"

            st.caption(
                f"{opportunity_type} · {subject} · {cost_label}"
            )

            # Show the deadline and flag upcoming or past dates.
            deadline_text = (
                opp.get("Deadline") or "No deadline listed"
            )
            parsed_deadline = parse_deadline(opp.get("Deadline"))

            if parsed_deadline is not None:
                days_left = (parsed_deadline - today).days

                if days_left < 0:
                    deadline_text += " · Deadline passed"
                elif days_left == 0:
                    deadline_text += " · Due today"
                elif days_left <= 14:
                    deadline_text += f" · {days_left} days left"

            st.write(f"**Deadline:** {deadline_text}")

            if tags:
                st.write("**Topics:** " + ", ".join(tags))
            else:
                st.write("**Topics:** Not listed")

            description = opp.get("Description")
            if description:
                st.write(description)

            # Only show a website link when one is available.
            link = opp.get("Link")
            if isinstance(link, str) and link.strip().startswith(
                ("https://", "http://")
            ):
                st.markdown(
                    f"[Visit the official website]({link.strip()})"
                )
            else:
                st.caption("Website link not available.")

            # Let users save an opportunity for later.
            if not user:
                st.caption(
                    "Enter your name in the sidebar to save opportunities."
                )
            elif opp_id is None:
                st.caption("This opportunity cannot be saved right now.")
            elif opp_id in saved_ids:
                if st.button(
                    "Remove from saved",
                    key=f"remove_{opp_id}",
                ):
                    remove(user, opp_id)
                    st.rerun()
            else:
                if st.button(
                    "Save opportunity",
                    key=f"save_{opp_id}",
                ):
                    save(user, opp_id)
                    st.rerun()

            st.divider()