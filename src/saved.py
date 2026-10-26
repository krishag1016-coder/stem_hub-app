import streamlit as st
from datetime import datetime, date
from src.database import supabase

TABLE = "Saved"


def current_user():
    """Sidebar name box. The name keys the saved list (simple, no passwords)."""
    name = st.sidebar.text_input(
        "👤 Your name (keeps your saved list)",
        value=st.session_state.get("user", ""),
        placeholder="e.g. Alex",
    )
    st.session_state["user"] = name
    return name.strip().lower() or None


def _local():
    return st.session_state.setdefault("saved_local", {})


def get_saved(user):
    """Returns {opportunity_id: notes}."""
    try:
        r = supabase.table(TABLE).select("opportunity_id,notes").eq("user_name", user).execute()
        return {row["opportunity_id"]: (row.get("notes") or "") for row in r.data}
    except Exception:
        return dict(_local().get(user, {}))


def save(user, opp_id):
    try:
        supabase.table(TABLE).upsert(
            {"user_name": user, "opportunity_id": opp_id},
            on_conflict="user_name,opportunity_id",
            ignore_duplicates=True,
        ).execute()
    except Exception:
        _local().setdefault(user, {}).setdefault(opp_id, "")


def remove(user, opp_id):
    try:
        supabase.table(TABLE).delete().eq("user_name", user).eq("opportunity_id", opp_id).execute()
    except Exception:
        _local().get(user, {}).pop(opp_id, None)


def update_notes(user, opp_id, notes):
    try:
        supabase.table(TABLE).update({"notes": notes}).eq("user_name", user).eq("opportunity_id", opp_id).execute()
    except Exception:
        _local().setdefault(user, {})[opp_id] = notes


def parse_deadline(deadline_str):
    """Returns a date, or None for 'Rolling', 'TBD', etc."""
    if not deadline_str:
        return None
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(deadline_str.strip(), fmt).date()
        except ValueError:
            continue
    return None