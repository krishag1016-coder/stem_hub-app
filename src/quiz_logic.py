"""
Scoring logic for the STEM Pathway Matcher quiz.

Design:
- Every answer option nudges one or more *Subjects* (the exact strings used
  in the Supabase "Subject" column / scraper.py, so results plug directly
  into the Directory filters).
- Every answer option ALSO nudges one or more *nuance tags* in the
  background (sub-interests like "AI/Machine Learning" or "Robotics").
  These aren't shown as the headline result, but surface in the full
  overview so the recommendation feels specific, not just a single label.
"""

from collections import defaultdict

# Keep this list identical to the Subject options the scraper assigns
# (see scraper.py's AI prompt) so quiz results always match real data.
SUBJECTS = [
    "Computer Science",
    "Engineering",
    "Biology",
    "Chemistry",
    "Physics",
    "Mathematics",
    "Earth & Environmental Science",
    "Interdisciplinary STEM",
]

QUIZ_QUESTIONS = [
    {
        "id": "q1",
        "question": "1. What kind of problems excite you most?",
        "options": [
            {
                "text": "Building apps, automating things, and writing code architecture.",
                "subject_weights": {"Computer Science": 3, "Engineering": 1},
                "tag_weights": {"Software Development": 2, "AI/Machine Learning": 1},
            },
            {
                "text": "Designing and building physical things that solve real problems.",
                "subject_weights": {"Engineering": 3, "Computer Science": 1},
                "tag_weights": {"Robotics": 2, "Mechanical Design": 1},
            },
            {
                "text": "Understanding how living things work, grow, and interact.",
                "subject_weights": {"Biology": 3},
                "tag_weights": {"Genetics": 1, "Ecology": 1},
            },
            {
                "text": "Finding hidden patterns in messy data and statistics.",
                "subject_weights": {"Mathematics": 2, "Computer Science": 2},
                "tag_weights": {"Data Science": 2, "Statistics & Data Analysis": 1},
            },
        ],
    },
    {
        "id": "q2",
        "question": "2. Pick a weekend project that sounds most fun:",
        "options": [
            {
                "text": "Training a small AI model or building a website from scratch.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"AI/Machine Learning": 2, "Software Development": 1},
            },
            {
                "text": "Mixing household chemicals safely to see reactions happen.",
                "subject_weights": {"Chemistry": 3},
                "tag_weights": {"Organic Chemistry": 1, "Materials Science": 1},
            },
            {
                "text": "Building a rocket, bridge, or robot out of spare parts.",
                "subject_weights": {"Engineering": 3, "Physics": 1},
                "tag_weights": {"Aerospace": 1, "Robotics": 2},
            },
            {
                "text": "Mapping local trails, weather, or water quality in your area.",
                "subject_weights": {"Earth & Environmental Science": 3},
                "tag_weights": {"Climate Science": 1, "Geology": 1},
            },
        ],
    },
    {
        "id": "q3",
        "question": "3. Which school subject do you actually look forward to?",
        "options": [
            {
                "text": "Calculus / advanced math theory.",
                "subject_weights": {"Mathematics": 3},
                "tag_weights": {"Pure Math / Theory": 2},
            },
            {
                "text": "Physics — motion, energy, forces.",
                "subject_weights": {"Physics": 3},
                "tag_weights": {"Applied Physics": 1, "Astrophysics": 1},
            },
            {
                "text": "Biology / anatomy / environmental science.",
                "subject_weights": {"Biology": 2, "Earth & Environmental Science": 2},
                "tag_weights": {"Neuroscience": 1, "Sustainability": 1},
            },
            {
                "text": "Computer science / coding electives.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"Cybersecurity": 1, "Software Development": 1},
            },
        ],
    },
    {
        "id": "q4",
        "question": "4. How do you prefer to work?",
        "options": [
            {
                "text": "Alone, deep in a screen, debugging until it works.",
                "subject_weights": {"Computer Science": 2, "Mathematics": 1},
                "tag_weights": {"Software Development": 1, "Pure Math / Theory": 1},
            },
            {
                "text": "Hands-on, building/testing a physical prototype.",
                "subject_weights": {"Engineering": 3},
                "tag_weights": {"Mechanical Design": 1, "Civil/Structural": 1},
            },
            {
                "text": "In a lab, running experiments and recording results.",
                "subject_weights": {"Chemistry": 2, "Biology": 2},
                "tag_weights": {"Biochemistry": 1, "Biotechnology": 1},
            },
            {
                "text": "On a team, connecting ideas across totally different fields.",
                "subject_weights": {"Interdisciplinary STEM": 3},
                "tag_weights": {"Design & Innovation": 1, "STEM Policy & Ethics": 1},
            },
        ],
    },
    {
        "id": "q5",
        "question": "5. What kind of impact do you want your work to have?",
        "options": [
            {
                "text": "Ship a tool or app millions of people can use.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"Software Development": 2},
            },
            {
                "text": "Help fight climate change or protect natural resources.",
                "subject_weights": {"Earth & Environmental Science": 3},
                "tag_weights": {"Climate Science": 2, "Sustainability": 1},
            },
            {
                "text": "Contribute to a medical or biological breakthrough.",
                "subject_weights": {"Biology": 3, "Chemistry": 1},
                "tag_weights": {"Biotechnology": 2, "Neuroscience": 1},
            },
            {
                "text": "Push the boundaries of what we understand about the universe.",
                "subject_weights": {"Physics": 3, "Mathematics": 1},
                "tag_weights": {"Astrophysics": 2, "Quantum Computing": 1},
            },
        ],
    },
    {
        "id": "q6",
        "question": "6. A machine breaks. What's your instinct?",
        "options": [
            {
                "text": "Check the code/firmware — it's probably a logic bug.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"Software Development": 1, "Cybersecurity": 1},
            },
            {
                "text": "Take it apart and inspect the physical mechanism.",
                "subject_weights": {"Engineering": 3},
                "tag_weights": {"Mechanical Design": 2},
            },
            {
                "text": "Model the forces/energy involved to see what failed.",
                "subject_weights": {"Physics": 3},
                "tag_weights": {"Applied Physics": 2},
            },
            {
                "text": "Run the numbers — was this predictable from the data?",
                "subject_weights": {"Mathematics": 3},
                "tag_weights": {"Statistics & Data Analysis": 2, "Applied Math / Modeling": 1},
            },
        ],
    },
    {
        "id": "q7",
        "question": "7. Pick a topic you'd happily read a whole article about:",
        "options": [
            {
                "text": "How large language models actually work.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"AI/Machine Learning": 2},
            },
            {
                "text": "How CRISPR gene-editing works.",
                "subject_weights": {"Biology": 3},
                "tag_weights": {"Genetics": 2, "Biotechnology": 1},
            },
            {
                "text": "How new battery materials are changing energy storage.",
                "subject_weights": {"Chemistry": 3, "Engineering": 1},
                "tag_weights": {"Materials Science": 2},
            },
            {
                "text": "How STEM education policy affects who gets access to it.",
                "subject_weights": {"Interdisciplinary STEM": 3},
                "tag_weights": {"STEM Education & Outreach": 2, "STEM Policy & Ethics": 1},
            },
        ],
    },
    {
        "id": "q8",
        "question": "8. Which future job sounds most appealing?",
        "options": [
            {
                "text": "Software engineer or AI researcher.",
                "subject_weights": {"Computer Science": 3},
                "tag_weights": {"AI/Machine Learning": 1, "Software Development": 1},
            },
            {
                "text": "Aerospace, mechanical, or civil engineer.",
                "subject_weights": {"Engineering": 3},
                "tag_weights": {"Aerospace": 1, "Civil/Structural": 1},
            },
            {
                "text": "Doctor, biomedical researcher, or environmental scientist.",
                "subject_weights": {"Biology": 2, "Earth & Environmental Science": 2},
                "tag_weights": {"Biotechnology": 1, "Climate Science": 1},
            },
            {
                "text": "Data scientist, actuary, or quantitative analyst.",
                "subject_weights": {"Mathematics": 3, "Computer Science": 1},
                "tag_weights": {"Statistics & Data Analysis": 2},
            },
        ],
    },
]


def calculate_results(selected_options):
    """
    selected_options: list, same length/order as QUIZ_QUESTIONS, containing
    the chosen option dict for each answered question (or None if skipped).

    Returns None if nothing was answered. Otherwise returns a dict with the
    top Subject match (for Directory filtering), the full subject ranking,
    and the top background nuance tags.
    """
    subject_scores = defaultdict(float)
    tag_scores = defaultdict(float)
    answered = 0

    for option in selected_options:
        if option is None:
            continue
        answered += 1
        for subject, weight in option.get("subject_weights", {}).items():
            subject_scores[subject] += weight
        for tag, weight in option.get("tag_weights", {}).items():
            tag_scores[tag] += weight

    if answered == 0:
        return None

    ranked_subjects = sorted(subject_scores.items(), key=lambda kv: kv[1], reverse=True)
    ranked_tags = sorted(tag_scores.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "answered": answered,
        "total_questions": len(selected_options),
        "subject_scores": dict(subject_scores),
        "tag_scores": dict(tag_scores),
        "ranked_subjects": ranked_subjects,
        "ranked_tags": ranked_tags,
        "top_subject": ranked_subjects[0][0] if ranked_subjects else None,
        "top_tags": [tag for tag, score in ranked_tags[:4] if score > 0],
    }
