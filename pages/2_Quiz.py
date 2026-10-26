import streamlit as st
from src.quiz_logic import QUIZ_QUESTIONS, calculate_results
from src.database import get_filtered_opportunities


st.set_page_config(
    page_title="StemHub | STEM Pathway Matcher",
    layout="wide",
)

st.header("Find your place in STEM")
st.write(
    "Not sure which area of STEM interests you most? Answer a few questions "
    "to see which subjects fit your interests and what kinds of programs "
    "you might want to explore."
)

st.divider()


# Keep track of each answer so the results reflect the user's choices.
selected_options = []

for question in QUIZ_QUESTIONS:
    option_labels = [option["text"] for option in question["options"]]

    choice = st.radio(
        question["question"],
        option_labels,
        index=None,
        key=f"quiz_{question['id']}",
    )

    matched_option = next(
        (
            option
            for option in question["options"]
            if option["text"] == choice
        ),
        None,
    )

    selected_options.append(matched_option)


st.divider()


# Calculate the results when the user is ready.
if st.button("Find My STEM Match", type="primary"):
    answered_count = sum(
        option is not None for option in selected_options
    )

    if answered_count == 0:
        st.warning("Choose at least one answer to see your results.")

    else:
        if answered_count < len(QUIZ_QUESTIONS):
            st.info(
                f"You answered {answered_count} of "
                f"{len(QUIZ_QUESTIONS)} questions. "
                "You can still see your results, but answering every "
                "question may give you a more complete match."
            )

        results = calculate_results(selected_options)
        top_subject = results["top_subject"]

        st.success(f"Your strongest match: {top_subject}")

        # Show the other subjects too, since interests can overlap.
        st.markdown("### Your results across STEM")

        ranked_subjects = results.get("ranked_subjects", [])
        max_score = (
            ranked_subjects[0][1]
            if ranked_subjects
            else 0
        )

        if ranked_subjects:
            for subject, score in ranked_subjects:
                st.write(f"**{subject}**")

                progress = (
                    min(max(score / max_score, 0), 1)
                    if max_score > 0
                    else 0
                )

                st.progress(progress)

        # These tags give a little more detail about the user's interests.
        top_tags = results.get("top_tags", [])

        if top_tags:
            st.markdown("### What else might interest you?")
            st.write(
                "Your answers also point toward these topics: "
                + ", ".join(top_tags)
            )

        # Find real opportunities related to the top subject.
        st.markdown("### Opportunities to explore")

        try:
            matches = get_filtered_opportunities(
                selected_subject=top_subject
            ) or []
        except Exception:
            matches = None
            st.warning(
                "We couldn't load matching opportunities right now. "
                "You can still browse everything on the Directory page."
            )

        if matches == []:
            st.info(
                f"There aren't any opportunities listed under "
                f"**{top_subject}** yet. Check the Directory page to "
                "explore what's currently available."
            )

        elif matches:
            top_tag_set = set(top_tags)

            # Put opportunities with overlapping topic tags first.
            def overlap_score(opportunity):
                tags = opportunity.get("Tags")
                if not isinstance(tags, list):
                    tags = []

                return len(
                    top_tag_set.intersection(
                        str(tag) for tag in tags
                    )
                )

            matches = sorted(
                matches,
                key=overlap_score,
                reverse=True,
            )

            for opportunity in matches[:5]:
                title = (
                    opportunity.get("Title")
                    or "Untitled opportunity"
                )

                st.write(f"**{title}**")

                opportunity_type = (
                    opportunity.get("Type") or "Type not listed"
                )
                deadline = (
                    opportunity.get("Deadline") or "No deadline listed"
                )

                tags = opportunity.get("Tags")
                if not isinstance(tags, list):
                    tags = []

                st.caption(
                    f"{opportunity_type} · Deadline: {deadline}"
                )

                if tags:
                    st.write("Topics: " + ", ".join(str(tag) for tag in tags))

                link = opportunity.get("Link")
                if isinstance(link, str) and link.strip().startswith(
                    ("https://", "http://")
                ):
                    st.markdown(
                        f"[Visit the official website]({link.strip()})"
                    )
                else:
                    st.caption("Website link not available.")

                st.divider()

            if len(matches) > 5:
                st.caption(
                    f"Showing 5 of {len(matches)} matching opportunities. "
                    "Visit the Directory page to explore more."
                )