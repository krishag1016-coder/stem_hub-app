import streamlit as st

st.header("📋 Your Personal STEM Dashboard")
st.write("Track upcoming application deadlines and save preparation notes.")

st.text_area("Add preparation notes for your upcoming competitions:", placeholder="e.g., Gather team for Hackathon by next Tuesday...")
if st.button("Save Notes"):
    st.success("Notes module running!")