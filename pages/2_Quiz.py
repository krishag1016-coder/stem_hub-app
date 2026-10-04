import streamlit as st
from src.quiz_logic import QUIZ_QUESTIONS, calculate_results
from src.database import get_filtered_opportunities

st.set_page_config(page_title="STEM Pathway Matcher", page_icon="🧠", layout="wide")

st.header("🧠 Personalized STEM Pathway Matcher")
st.write(
    "Answer these questions to find your best-fit STEM subject — plus the "
    "specific sub-interests behind that match."
)
st.markdown("---")

# --- STEP 1: RENDER QUESTIONS ---
# index=None means nothing is pre-selected, so we don't silently bias
# results toward whichever option happens to be listed first.
selected_options = []
for question in QUIZ_QUESTIONS:
    option_labels = [opt["text"] for opt in question["options"]]
    choice = st.radio(
        question["question"],
        option_labels,
        index=None,
        key=f"quiz_{question['id']}",
    )
    matched_option = next(
        (opt for opt in question["options"] if opt["text"] == choice), None
    )
    selected_options.append(matched_option)
    st.write("")

st.markdown("---")

# --- STEP 2: CALCULATE & DISPLAY RESULTS ---
if st.button("Calculate My Path", type="primary"):
    answered_count = sum(1 for opt in selected_options if opt is not None)

    if answered_count == 0:
        st.warning("Answer at least one question to see your results.")
    else:
        if answered_count < len(QUIZ_QUESTIONS):
            st.info(
                f"You answered {answered_count} of {len(QUIZ_QUESTIONS)} questions — "
                "answer all of them for the most accurate match."
            )

        results = calculate_results(selected_options)
        top_subject = results["top_subject"]

        st.success(f"🎯 Your top STEM match: **{top_subject}**")

        # Show the full subject breakdown, not just the winner, so the
        # person can see how close runner-up fields were.
        st.markdown("#### 📊 How you scored across every subject")
        max_score = results["ranked_subjects"][0][1] if results["ranked_subjects"] else 1
        for subject, score in results["ranked_subjects"]:
            st.write(f"**{subject}**")
            st.progress(min(score / max_score, 1.0) if max_score else 0)

        # Background nuance tags: the specific sub-interests behind the
        # headline subject match.
        if results["top_tags"]:
            st.markdown("#### 🔍 Your specific sub-interests")
            st.write(
                "Beyond the subject itself, your answers lean toward: "
                + ", ".join(f"`{tag}`" for tag in results["top_tags"])
            )

        # --- STEP 3: PULL REAL MATCHING OPPORTUNITIES FROM SUPABASE ---
        st.markdown("#### 📋 Opportunities that match your result")
        matches = get_filtered_opportunities(selected_subject=top_subject)

        if not matches:
            st.info(
                f"No opportunities tagged **{top_subject}** are in the database yet. "
                "Check the Directory page for everything currently available."
            )
        else:
            top_tag_set = set(results["top_tags"])
            # Surface opportunities that also overlap with the nuance tags first.
            def overlap_score(opp):
                opp_tags = opp.get("Tags") if isinstance(opp.get("Tags"), list) else []
                return len(top_tag_set.intersection(opp_tags))

            matches.sort(key=overlap_score, reverse=True)

            for opp in matches[:5]:
                opp_tags = opp.get("Tags", []) if isinstance(opp.get("Tags"), list) else []
                highlight = " ⭐" if overlap_score(opp) > 0 else ""
                st.write(f"**{opp.get('Title')}**{highlight}")
                st.write(
                    f"💼 {opp.get('Type')} | 🗓️ {opp.get('Deadline', 'TBD')} | "
                    f"🏷️ {', '.join(opp_tags) if opp_tags else 'No tags'}"
                )
                st.markdown(f"[Visit Official Website]({opp.get('Link')})")
                st.markdown("---")

            if len(matches) > 5:
                st.caption(
                    f"Showing 5 of {len(matches)} matches — visit the Directory page "
                    f"and filter by **{top_subject}** to see the rest."
                )
