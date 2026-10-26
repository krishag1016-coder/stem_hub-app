import streamlit as st
from datetime import date
from src.database import supabase
from src.saved import (
    current_user,
    get_saved,
    remove,
    update_notes,
    parse_deadline,
)


st.set_page_config(
    page_title="StemHub | My Dashboard",
    layout="wide",
)

st.header("My STEM Dashboard")
st.write(
    "Keep track of opportunities you've saved, check upcoming deadlines, "
    "and jot down notes as you prepare to apply."
)


# A user needs to enter their name before viewing saved items.
user = current_user()

if not user:
    st.info("Enter your name in the sidebar to see your saved opportunities.")
    st.stop()


# Get the opportunities this user has saved.
saved = get_saved(user)

if not saved:
    st.info(
        "You haven't saved anything yet. Head to the Directory and save "
        "opportunities you'd like to come back to."
    )
    st.stop()


# Fetch the full details for the saved opportunities.
try:
    response = (
        supabase.table("Opportunities")
        .select("*")
        .in_("id", list(saved.keys()))
        .execute()
    )
    rows = response.data or []
except Exception:
    st.error(
        "We couldn't load your saved opportunities right now. "
        "Please try again later."
    )
    st.stop()


# Work out how far away each deadline is.
today = date.today()
items = []

for opp in rows:
    deadline = parse_deadline(opp.get("Deadline"))
    days_left = (deadline - today).days if deadline else None
    items.append((opp, days_left))


# Show upcoming deadlines first, followed by undated items and expired ones.
def sort_key(item):
    days_left = item[1]

    if days_left is None:
        return (1, 0)

    if days_left < 0:
        return (2, 0)

    return (0, days_left)


items.sort(key=sort_key)

upcoming = [
    days_left
    for _, days_left in items
    if days_left is not None and days_left >= 0
]

due_soon = [
    days_left
    for days_left in upcoming
    if days_left <= 14
]


# Give users a quick overview of what's on their list.
col1, col2, col3 = st.columns(3)

col1.metric("Saved opportunities", len(items))
col2.metric("Due in the next 14 days", len(due_soon))
col3.metric(
    "Next deadline",
    f"{min(upcoming)} days" if upcoming else "No upcoming deadlines",
)

st.divider()


# Turn each deadline into a short, readable status.
def status_label(days_left, deadline):
    if days_left is None:
        return deadline or "Deadline not listed"

    if days_left < 0:
        return "Deadline passed"

    if days_left == 0:
        return "Due today"

    if days_left == 1:
        return "1 day left"

    return f"{days_left} days left"


# Display each saved opportunity along with its notes.
for opp, days_left in items:
    opp_id = opp.get("id")

    with st.container():
        left, right = st.columns([3, 1])

        left.subheader(opp.get("Title") or "Untitled opportunity")
        right.markdown(
            f"**{status_label(days_left, opp.get('Deadline'))}**"
        )

        opportunity_type = opp.get("Type") or "Type not listed"
        subject = opp.get("Subject") or "Subject not listed"

        # Avoid labeling an opportunity as free if its cost is unknown.
        raw_cost = opp.get("Is_Paid")

        if isinstance(raw_cost, bool):
            is_paid = raw_cost
        elif isinstance(raw_cost, (int, float)) and raw_cost in (0, 1):
            is_paid = bool(raw_cost)
        elif isinstance(raw_cost, str):
            value = raw_cost.strip().casefold()

            if value in {"true", "1", "yes"}:
                is_paid = True
            elif value in {"false", "0", "no"}:
                is_paid = False
            else:
                is_paid = None
        else:
            is_paid = None

        if is_paid is True:
            cost_label = "Paid"
        elif is_paid is False:
            cost_label = "Free / fully funded"
        else:
            cost_label = "Cost not listed"

        st.caption(
            f"{opportunity_type} · {subject} · {cost_label}"
        )

        description = opp.get("Description")
        if description:
            st.write(description)

        # Only show a website link when a valid-looking URL is available.
        link = opp.get("Link")

        if isinstance(link, str) and link.strip().startswith(
            ("https://", "http://")
        ):
            st.markdown(
                f"[Visit the official website]({link.strip()})"
            )
        else:
            st.caption("Website link not available.")

        # Keep personal planning notes attached to each saved opportunity.
        notes = st.text_area(
            "My notes",
            value=saved.get(opp_id, "") or "",
            key=f"notes_{opp_id}",
            placeholder=(
                "Application ideas, requirements, people to contact, "
                "or questions to look into..."
            ),
        )

        col_save, col_remove, _ = st.columns([1, 1, 4])

        if col_save.button("Save notes", key=f"save_notes_{opp_id}"):
            try:
                update_notes(user, opp_id, notes)
                st.toast("Notes saved.")
            except Exception:
                st.error("We couldn't save your notes. Please try again.")

        if col_remove.button("Remove saved item", key=f"remove_{opp_id}"):
            try:
                remove(user, opp_id)
                st.rerun()
            except Exception:
                st.error("We couldn't remove this opportunity. Please try again.")

        st.divider()