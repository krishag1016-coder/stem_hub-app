import streamlit as st

st.header("🧠 Personalized STEM Pathway Matcher")
st.write("Answer these cognitive and technical preference questions to find your ideal field.")

q1 = st.radio("1. What kind of problems excite you most?", [
    "Building applications, automation, and writing code architecture.",
    "Understanding how humans think, learn, process language, and interact with technology.",
    "Finding hidden patterns in messy data, analyzing trends, and statistics."
])

if st.button("Calculate My Path"):
    st.success("In progress!")