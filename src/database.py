from supabase import create_client, Client
import streamlit as st

# 1. Initialize your Supabase Client
# Replace these strings with your actual project credentials from your Supabase settings!
SUPABASE_URL = "https://coogbyxcvsrwgdwfexbe.supabase.co"  
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNvb2dieXhjdnNyd2dkd2ZleGJlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM4OTk2NzEsImV4cCI6MjA5OTQ3NTY3MX0.Uu6QbIa9MhV5c49YWGc0hlTt_5ONfOMGLsEq7eN7oJc"
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