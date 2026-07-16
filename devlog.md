# 📓 Development Log: STEM Opportunity Finder

Welcome to my build diary! This is where I document my progress, architectural decisions, failures, and breakthroughs as I build this AI-powered platform.

---

## 🚀 The Master Plan
- [x] Phase 1: Core scraper & direct Hugging Face integration
- [x] Phase 2: Supabase database setup & duplicate prevention
- [ ] Phase 3: Build the Streamlit frontend UI & search filters
- [ ] Phase 4: Implement advanced features (Paid vs. Free filter)
- [ ] Phase 5: Deployment & Public Launch

---

## ✍️ Daily Logs

### 📅 June 15, 2026 - The API Migration & Database Shield
- **Goal:** Get the scraper working with real live data and prevent database duplicates.
- **What I Did:**
  - Migrated the Hugging Face API connection from the local SDK to a direct HTTPS `requests` connection using the upgraded V1 Chat Router. This bypassed a major network connection error on my local machine.
  - Linked the script back to a live repository source URL (`https://raw.githubusercontent.com/...`) to parse real opportunities dynamically.
  - Implemented a pre-upload verification step in python to query Supabase first. If an opportunity title already exists, the script gracefully skips it instead of crashing.
  - Implemented regular-expression-based parsing and python helper functions to force Llama-3 to only return a single-subject tag instead of comma-separated lists.
- **Biggest Struggle:** Figuring out why the scraper crashed on duplicates.
- **What I Learned:** Database constraints are powerful, but your backend code needs to handle potential constraint errors gracefully to prevent pipeline crashes.
- **Next Steps:** Connect the Streamlit dashboard to Supabase to display these freshly scraped opportunities.

---

### 📅 [Next Date] - [Quick Title]
- **Goal:** - **What I Did:**
- **Biggest Struggle:**
- **What I Learned:**
- **Next Steps:**