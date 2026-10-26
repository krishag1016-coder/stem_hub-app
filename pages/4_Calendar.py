import calendar
import html
import streamlit as st
from datetime import date, datetime, timedelta, timezone
from src.database import supabase
from src.saved import current_user, get_saved, parse_deadline

st.set_page_config(page_title="Deadline Calendar", page_icon="🗓️", layout="wide")

st.header("🗓️ Deadline Calendar")
st.write("See every deadline at a glance, and add them to your own calendar.")

user = current_user()
saved_ids = set(get_saved(user).keys()) if user else set()

# --- FETCH DATA ---
try:
    all_opps = supabase.table("Opportunities").select("*").execute().data or []
except Exception as e:
    st.error(f"Error connecting to database: {e}")
    all_opps = []

# --- CONTROLS ---
ctrl1, ctrl2 = st.columns(2)
with ctrl1:
    view = st.radio("Show:", ["All opportunities", "Only my saved"], horizontal=True)
with ctrl2:
    subjects = sorted({o.get("Subject") for o in all_opps if o.get("Subject")})
    chosen_subjects = st.multiselect("Subject:", subjects, placeholder="All Subjects")

opps = all_opps
if view == "Only my saved":
    opps = [o for o in opps if o.get("id") in saved_ids]
    if not user:
        st.info("👈 Enter your name in the sidebar to see your saved deadlines here.")
    elif not opps:
        st.info("You haven't saved anything yet. Save opportunities from the Directory and they'll show up here.")
if chosen_subjects:
    opps = [o for o in opps if o.get("Subject") in chosen_subjects]

# --- SORT INTO DATED / UNDATED ---
today = date.today()
by_date = {}
undated = []
for opp in opps:
    d = parse_deadline(opp.get("Deadline"))
    # The scraper uses year 2099 when a page gives no year, so treat that
    # as "date not confirmed" instead of putting it on the calendar.
    if d is None or d.year >= 2090:
        undated.append(opp)
    else:
        by_date.setdefault(d, []).append(opp)

# --- MONTH NAVIGATION ---
st.session_state.setdefault("cal_year", today.year)
st.session_state.setdefault("cal_month", today.month)

nav1, nav2, nav3, nav4 = st.columns([1, 3, 1, 1])
if nav1.button("◀ Prev"):
    if st.session_state.cal_month == 1:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
    else:
        st.session_state.cal_month -= 1
    st.rerun()
if nav3.button("Next ▶"):
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

year, month = st.session_state.cal_year, st.session_state.cal_month
nav2.markdown(f"<h3 style='text-align:center;margin:0'>{calendar.month_name[month]} {year}</h3>", unsafe_allow_html=True)

# --- BUILD THE MONTH GRID ---
CSS = (
    "<style>"
    ".cal{width:100%;border-collapse:collapse;table-layout:fixed;}"
    ".cal th{padding:6px;text-align:center;font-size:0.85rem;opacity:0.7;}"
    ".cal td{vertical-align:top;height:110px;border:1px solid rgba(128,128,128,0.3);padding:4px;font-size:0.75rem;}"
    ".cal td.empty{background:rgba(128,128,128,0.06);}"
    ".cal td.today{border:2px solid #ff4b4b;}"
    ".cal .num{font-weight:600;font-size:0.85rem;}"
    ".cal .ev{display:block;margin-top:3px;padding:2px 4px;border-radius:4px;background:rgba(255,75,75,0.18);"
    "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}"
    ".cal .ev.soon{background:rgba(255,75,75,0.38);}"
    ".cal .ev.saved{background:rgba(66,133,244,0.35);}"
    ".cal .ev.past{background:rgba(128,128,128,0.2);text-decoration:line-through;}"
    ".cal .more{opacity:0.7;font-size:0.7rem;margin-top:3px;}"
    "</style>"
)

cal = calendar.Calendar(firstweekday=6)  # weeks start on Sunday
rows = ["<table class='cal'><tr>" + "".join(f"<th>{n}</th>" for n in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) + "</tr>"]

for week in cal.monthdayscalendar(year, month):
    cells = []
    for day in week:
        if day == 0:
            cells.append("<td class='empty'></td>")
            continue
        d = date(year, month, day)
        cls = "today" if d == today else ""
        content = f"<div class='num'>{day}</div>"
        events = by_date.get(d, [])
        for opp in events[:3]:
            days_left = (d - today).days
            if opp.get("id") in saved_ids:
                ev_cls = "saved"
            elif days_left < 0:
                ev_cls = "past"
            elif days_left <= 14:
                ev_cls = "soon"
            else:
                ev_cls = ""
            title = html.escape(str(opp.get("Title") or ""))
            content += f"<span class='ev {ev_cls}' title='{title}'>{title}</span>"
        if len(events) > 3:
            content += f"<div class='more'>+{len(events) - 3} more</div>"
        cells.append(f"<td class='{cls}'>{content}</td>")
    rows.append("<tr>" + "".join(cells) + "</tr>")
rows.append("</table>")

st.markdown(CSS + "".join(rows), unsafe_allow_html=True)
st.caption("🔵 saved by you  |  🔴 due within 14 days  |  grey = already passed")

# --- THIS MONTH'S LIST ---
st.markdown(f"### Deadlines in {calendar.month_name[month]} {year}")
month_events = sorted(
    [(d, o) for d, lst in by_date.items() if d.year == year and d.month == month for o in lst],
    key=lambda pair: pair[0],
)
if not month_events:
    st.write("No deadlines this month.")
else:
    for d, opp in month_events:
        days_left = (d - today).days
        if days_left < 0:
            tag = "⛔ passed"
        elif days_left == 0:
            tag = "🔥 due today"
        else:
            tag = f"{days_left} days left"
        st.markdown(
            f"**{d.strftime('%b %d')}** — {opp.get('Title')} "
            f"({opp.get('Subject')}) · {tag} · [Website]({opp.get('Link')})"
        )

# --- UNDATED ---
if undated:
    with st.expander(f"No exact date ({len(undated)}) — rolling, TBD, or year not listed"):
        for opp in undated:
            st.markdown(f"**{opp.get('Title')}** — {opp.get('Deadline') or 'TBD'} · [Website]({opp.get('Link')})")


# --- CALENDAR FILE (.ics) EXPORT ---
def ics_escape(text):
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_ics(events):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//STEM Hub//Deadlines//EN", "CALSCALE:GREGORIAN"]
    for d, opp in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:stemhub-{opp.get('id')}-{d:%Y%m%d}@stemhub",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{(d + timedelta(days=1)):%Y%m%d}",
            f"SUMMARY:{ics_escape('Deadline: ' + str(opp.get('Title') or ''))}",
            f"DESCRIPTION:{ics_escape(opp.get('Description'))}",
        ]
        link = str(opp.get("Link") or "")
        if link.startswith("http"):
            lines.append(f"URL:{link}")
        # reminder one week before the deadline
        lines += [
            "BEGIN:VALARM",
            "TRIGGER:-P7D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{ics_escape('One week until: ' + str(opp.get('Title') or ''))}",
            "END:VALARM",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


st.markdown("---")
st.markdown("### ➕ Add to your own calendar")
upcoming = sorted(
    [(d, o) for d, lst in by_date.items() if d >= today for o in lst],
    key=lambda pair: pair[0],
)

dl1, dl2 = st.columns(2)
with dl1:
    st.download_button(
        f"Download {calendar.month_name[month]}'s deadlines (.ics)",
        data=build_ics(month_events),
        file_name=f"stem_deadlines_{year}_{month:02d}.ics",
        mime="text/calendar",
        disabled=not month_events,
    )
with dl2:
    st.download_button(
        f"Download all upcoming deadlines (.ics) — {len(upcoming)}",
        data=build_ics(upcoming),
        file_name="stem_deadlines_upcoming.ics",
        mime="text/calendar",
        disabled=not upcoming,
    )
st.caption("Open the downloaded file to add the deadlines to Google Calendar, Apple Calendar or Outlook. Each one includes a reminder a week before.")