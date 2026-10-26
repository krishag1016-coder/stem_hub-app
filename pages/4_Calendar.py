import calendar
import html
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import streamlit as st

from src.database import supabase
from src.saved import current_user, get_saved, parse_deadline


st.set_page_config(
    page_title="StemHub | Deadline Calendar",
    layout="wide",
)

st.header("Deadline Calendar")
st.write(
    "Keep track of application deadlines, see what's coming up, "
    "and add confirmed dates to your own calendar."
)


# Get the user's saved opportunities.
user = current_user()
saved_ids = set(get_saved(user).keys()) if user else set()


# Load the opportunities from the database.
try:
    response = supabase.table("Opportunities").select("*").execute()
    all_opps = response.data or []
except Exception:
    st.error(
        "We couldn't load the calendar right now. "
        "Please try again later."
    )
    st.stop()


# Try the existing date parser first, then handle common date formats.
def get_deadline(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text or text.casefold() in {
        "tbd", "rolling", "varies", "not specified",
        "no deadline", "none", "n/a", "na",
    }:
        return None

    # A placeholder year should not be treated as a confirmed deadline.
    if re.search(r"\b(?:209\d|9999)\b", text):
        return None

    try:
        parsed = parse_deadline(text)
        if parsed is not None and parsed.year < 2090:
            return parsed
    except (TypeError, ValueError, OverflowError):
        pass

    # Handle common database and spreadsheet date formats.
    formats = (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt).date()
            if parsed.year < 2090:
                return parsed
        except ValueError:
            continue

    return None


# Keep the cost field consistent even if older rows contain strings.
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


# Filter by saved status and subject.
ctrl1, ctrl2 = st.columns(2)

with ctrl1:
    view = st.radio(
        "Show",
        ["All opportunities", "Only my saved"],
        horizontal=True,
    )

with ctrl2:
    subjects = sorted({
        str(opp["Subject"])
        for opp in all_opps
        if opp.get("Subject")
    })

    chosen_subjects = st.multiselect(
        "Subject",
        subjects,
        placeholder="All subjects",
    )

opps = all_opps

if view == "Only my saved":
    if not user:
        st.info(
            "Enter your name in the sidebar to see your saved deadlines."
        )
        opps = []
    else:
        opps = [
            opp for opp in opps
            if opp.get("id") in saved_ids
        ]

        if not opps:
            st.info(
                "You haven't saved any opportunities yet. "
                "Save some from the Directory to see them here."
            )

if chosen_subjects:
    opps = [
        opp for opp in opps
        if opp.get("Subject") in chosen_subjects
    ]


# Separate confirmed dates from opportunities without a usable date.
today = date.today()
by_date = {}
undated = []

for opp in opps:
    deadline = get_deadline(opp.get("Deadline"))

    if deadline is None:
        undated.append(opp)
    else:
        by_date.setdefault(deadline, []).append(opp)


# Move between months without losing the current view.
st.session_state.setdefault("cal_year", today.year)
st.session_state.setdefault("cal_month", today.month)

nav1, nav2, nav3, nav4 = st.columns([1, 3, 1, 1])

if nav1.button("Previous"):
    if st.session_state.cal_month == 1:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
    else:
        st.session_state.cal_month -= 1
    st.rerun()

if nav3.button("Next"):
    if st.session_state.cal_month == 12:
        st.session_state.cal_month = 1
        st.session_state.cal_year += 1
    else:
        st.session_state.cal_month += 1
    st.rerun()

if nav4.button("Today"):
    st.session_state.cal_year = today.year
    st.session_state.cal_month = today.month
    st.rerun()

year = st.session_state.cal_year
month = st.session_state.cal_month

nav2.markdown(
    f"<h3 style='text-align:center;margin:0'>"
    f"{calendar.month_name[month]} {year}</h3>",
    unsafe_allow_html=True,
)


# Build the month grid. Escape opportunity titles before putting them in HTML.
css = """
<style>
.cal {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}
.cal th {
    padding: 6px;
    text-align: center;
    font-size: 0.85rem;
    opacity: 0.7;
}
.cal td {
    vertical-align: top;
    height: 110px;
    border: 1px solid rgba(128,128,128,0.3);
    padding: 4px;
    font-size: 0.75rem;
    overflow-wrap: anywhere;
}
.cal td.empty {
    background: rgba(128,128,128,0.06);
}
.cal td.today {
    border: 2px solid #6CB670;
}
.cal .num {
    font-weight: 600;
    font-size: 0.85rem;
}
.cal .ev {
    display: block;
    margin-top: 3px;
    padding: 2px 4px;
    border-radius: 4px;
    background: rgba(108,182,112,0.18);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cal .ev.soon {
    background: rgba(108,182,112,0.38);
}
.cal .ev.saved {
    background: rgba(66,133,244,0.3);
}
.cal .ev.past {
    background: rgba(128,128,128,0.2);
    text-decoration: line-through;
}
.cal .more {
    opacity: 0.7;
    font-size: 0.7rem;
    margin-top: 3px;
}
</style>
"""

cal = calendar.Calendar(firstweekday=6)
weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

rows = [
    "<table class='cal'><thead><tr>"
    + "".join(f"<th>{day}</th>" for day in weekdays)
    + "</tr></thead><tbody>"
]

for week in cal.monthdayscalendar(year, month):
    cells = []

    for day in week:
        if day == 0:
            cells.append("<td class='empty'></td>")
            continue

        current_day = date(year, month, day)
        cell_class = "today" if current_day == today else ""
        content = f"<div class='num'>{day}</div>"

        events = by_date.get(current_day, [])

        for opp in events[:3]:
            days_left = (current_day - today).days

            if opp.get("id") in saved_ids:
                event_class = "saved"
            elif days_left < 0:
                event_class = "past"
            elif days_left <= 14:
                event_class = "soon"
            else:
                event_class = ""

            title = html.escape(
                str(opp.get("Title") or "Untitled opportunity"),
                quote=True,
            )

            content += (
                f"<span class='ev {event_class}' title='{title}'>"
                f"{title}</span>"
            )

        if len(events) > 3:
            content += (
                f"<div class='more'>+{len(events) - 3} more</div>"
            )

        cells.append(
            f"<td class='{cell_class}'>{content}</td>"
        )

    rows.append("<tr>" + "".join(cells) + "</tr>")

rows.append("</tbody></table>")

st.markdown(css + "".join(rows), unsafe_allow_html=True)

st.caption(
    "Green highlights indicate upcoming deadlines. "
    "Blue highlights indicate opportunities you've saved. "
    "Grey text indicates past deadlines."
)


# List every deadline in the month for easier reading.
st.markdown(f"### Deadlines in {calendar.month_name[month]} {year}")

month_events = sorted(
    [
        (deadline, opp)
        for deadline, opportunities in by_date.items()
        if deadline.year == year and deadline.month == month
        for opp in opportunities
    ],
    key=lambda item: item[0],
)

if not month_events:
    st.write("No confirmed deadlines this month.")
else:
    for deadline, opp in month_events:
        days_left = (deadline - today).days

        if days_left < 0:
            status = "Deadline passed"
        elif days_left == 0:
            status = "Due today"
        elif days_left == 1:
            status = "1 day left"
        else:
            status = f"{days_left} days left"

        title = opp.get("Title") or "Untitled opportunity"
        subject = opp.get("Subject") or "Subject not listed"

        st.markdown(
            f"**{deadline.strftime('%b %d, %Y')}** — "
            f"{title} · {subject} · {status}"
        )

        link = opp.get("Link")
        if isinstance(link, str):
            parsed_url = urlparse(link.strip())
            if parsed_url.scheme in {"https", "http"} and parsed_url.netloc:
                st.markdown(
                    f"[Visit the official website]({link.strip()})"
                )


# Keep rolling, TBD, and other undated opportunities accessible.
if undated:
    with st.expander(
        f"Opportunities without confirmed dates ({len(undated)})"
    ):
        for opp in undated:
            title = opp.get("Title") or "Untitled opportunity"
            deadline_text = opp.get("Deadline") or "No date listed"

            st.write(f"**{title}** — {deadline_text}")

            link = opp.get("Link")
            if isinstance(link, str):
                parsed_url = urlparse(link.strip())
                if parsed_url.scheme in {"https", "http"} and parsed_url.netloc:
                    st.markdown(
                        f"[Visit the official website]({link.strip()})"
                    )


# Create an iCalendar file so users can import confirmed deadlines.
def ics_escape(value):
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def build_ics(events):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StemHub//Deadline Calendar//EN",
        "CALSCALE:GREGORIAN",
    ]

    for deadline, opp in events:
        title = str(opp.get("Title") or "Untitled opportunity")
        description = str(opp.get("Description") or "")
        opportunity_id = opp.get("id", title)

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:stemhub-{ics_escape(opportunity_id)}-{deadline:%Y%m%d}@stemhub",
            f"DTSTAMP:{timestamp}",
            f"DTSTART;VALUE=DATE:{deadline:%Y%m%d}",
            f"DTEND;VALUE=DATE:{(deadline + timedelta(days=1)):%Y%m%d}",
            f"SUMMARY:{ics_escape('Deadline: ' + title)}",
            f"DESCRIPTION:{ics_escape(description)}",
        ])

        link = opp.get("Link")
        if isinstance(link, str):
            parsed_url = urlparse(link.strip())
            if parsed_url.scheme in {"https", "http"} and parsed_url.netloc:
                lines.append(f"URL:{link.strip()}")

        # Add a reminder one week before the deadline.
        lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-P7D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{ics_escape('One week until: ' + title)}",
            "END:VALARM",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


st.divider()
st.markdown("### Add deadlines to your calendar")

upcoming_events = sorted(
    [
        (deadline, opp)
        for deadline, opportunities in by_date.items()
        if deadline >= today
        for opp in opportunities
    ],
    key=lambda item: item[0],
)

download_col1, download_col2 = st.columns(2)

with download_col1:
    st.download_button(
        f"Download {calendar.month_name[month]}'s deadlines (.ics)",
        data=build_ics(month_events),
        file_name=f"stemhub_deadlines_{year}_{month:02d}.ics",
        mime="text/calendar",
        disabled=not month_events,
    )

with download_col2:
    st.download_button(
        f"Download upcoming deadlines ({len(upcoming_events)})",
        data=build_ics(upcoming_events),
        file_name="stemhub_upcoming_deadlines.ics",
        mime="text/calendar",
        disabled=not upcoming_events,
    )

st.caption(
    "Import the downloaded file into Google Calendar, Apple Calendar, "
    "or Outlook. Calendar reminders are set for one week before each date."
)