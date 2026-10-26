import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

load_dotenv()  # Load environment variables from .env file

def _get_secret(key):
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets.get(key)
    except Exception:
        return None

# 1. Initialize Supabase Client
# private keys stored elsewhere
SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_KEY = _get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "Missing supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY in your environment variables or Streamlit secrets."
        "in your .env file or Streamlit secrets.toml file."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. The filtering function your Directory is trying to import
def get_filtered_opportunities(selected_tag=None, selected_type=None, selected_subject=None):
    """Fetches opportunities from Supabase applying array tag and type filters."""
    try:
        # Start a basic query to select everything from your table
        query = supabase.table("Opportunities").select("*")
        
        # If the user selected a specific main subject, filter by it
        if selected_subject and selected_subject != "All Main Subjects":
            query = query.eq("Subject", selected_subject)
            
        # If the user selected a specific tag, check if it exists inside the tags array
        if selected_tag and selected_tag != "All Subjects":
            query = query.contains("Tags", [selected_tag])
            
        # If the user selected a specific opportunity type, filter by it
        if selected_type and selected_type != "All Types":
            query = query.eq("Type", selected_type)
            
        # Execute the query and send the data back to your website page
        response = query.execute()
        return response.data
        
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return []