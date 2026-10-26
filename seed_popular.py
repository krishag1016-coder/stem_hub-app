"""
Loads a hand-picked list of well-known STEM programs into the database.
Safe to run more than once: titles that already exist are skipped.
Deadlines start as "TBD"; run update_deadlines.py afterward to fill them in
from each program's official page.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.database import supabase

COMP = "Competitions/Hackathons"
RESEARCH = "Research & Fellowships"
INTERN = "Internships"
CAMP = "Summer Camps"


PROGRAMS = [
    # ---------------- Computer Science ----------------
    {"Title": "Congressional App Challenge", "Type": COMP, "Subject": "Computer Science",
     "Tags": ["App Development", "Software Development", "Coding"],
     "Link": "https://www.congressionalappchallenge.us", "Is_Paid": False,
     "Description": "A nationwide coding competition where middle and high school students build an original app and submit it to their U.S. House district, with winners recognized by their Member of Congress."},
    {"Title": "USA Computing Olympiad (USACO)", "Type": COMP, "Subject": "Computer Science",
     "Tags": ["Competitive Programming", "Algorithms", "Software Development"],
     "Link": "https://usaco.org", "Is_Paid": False,
     "Description": "An online programming contest series with tiered divisions from Bronze to Platinum, where strong performers can advance toward the U.S. team for the International Olympiad in Informatics."},
    {"Title": "Technovation Girls", "Type": COMP, "Subject": "Computer Science",
     "Tags": ["App Development", "AI/Machine Learning", "STEM Education & Outreach"],
     "Link": "https://technovation.org", "Is_Paid": False,
     "Description": "A free global program where girls work in teams with mentors to build a mobile app or AI project that tackles a problem in their community."},
    {"Title": "Girls Who Code Summer Programs", "Type": CAMP, "Subject": "Computer Science",
     "Tags": ["Coding", "Software Development", "STEM Education & Outreach"],
     "Link": "https://girlswhocode.com", "Is_Paid": False,
     "Description": "Free coding programs and clubs for girls and nonbinary students that teach programming and build a supportive community of peers."},

    # ---------------- Engineering ----------------
    {"Title": "FIRST Robotics Competition", "Type": COMP, "Subject": "Engineering",
     "Tags": ["Robotics", "Mechanical Design", "Design & Innovation"],
     "Link": "https://www.firstinspires.org/robotics/frc", "Is_Paid": True,
     "Description": "A team-based robotics competition where high school students design, build and program a robot to play a new game each season."},
    {"Title": "VEX Robotics Competition", "Type": COMP, "Subject": "Engineering",
     "Tags": ["Robotics", "Mechanical Design", "Coding"],
     "Link": "https://www.vexrobotics.com/competition", "Is_Paid": True,
     "Description": "A popular team robotics competition where students design and drive robots built on the VEX platform in head-to-head matches."},
    {"Title": "NASA High School Internships", "Type": INTERN, "Subject": "Engineering",
     "Tags": ["Aerospace", "Space Science", "Research"],
     "Link": "https://intern.nasa.gov", "Is_Paid": False,
     "Description": "NASA internship opportunities that let high school students work on real projects alongside NASA scientists and engineers."},

    # ---------------- Biology ----------------
    {"Title": "USA Biology Olympiad (USABO)", "Type": COMP, "Subject": "Biology",
     "Tags": ["Genetics", "Biotechnology", "Ecology"],
     "Link": "https://www.usabo-trc.org", "Is_Paid": False,
     "Description": "A multi-stage biology competition starting with an open exam, where top finishers can go on to represent the U.S. at the International Biology Olympiad."},
    {"Title": "iGEM High School", "Type": COMP, "Subject": "Biology",
     "Tags": ["Biotechnology", "Genetics", "Design & Innovation"],
     "Link": "https://igem.org", "Is_Paid": True,
     "Description": "An international synthetic biology competition with a high school division, where teams design and build genetically engineered systems to solve real problems."},
    {"Title": "Genes in Space", "Type": COMP, "Subject": "Biology",
     "Tags": ["Genetics", "Biotechnology", "Space Science"],
     "Link": "https://www.genesinspace.org", "Is_Paid": False,
     "Description": "A competition where students design a DNA experiment that could be carried out on the International Space Station."},

    # ---------------- Chemistry ----------------
    {"Title": "U.S. National Chemistry Olympiad (USNCO)", "Type": COMP, "Subject": "Chemistry",
     "Tags": ["Organic Chemistry", "Materials Science", "Biochemistry"],
     "Link": "https://www.acs.org/education/students/highschool/olympiad.html", "Is_Paid": False,
     "Description": "A chemistry competition run by the American Chemical Society, with local exams leading to national selection for the International Chemistry Olympiad."},

    # ---------------- Physics ----------------
    {"Title": "USA Physics Olympiad (F=ma and USAPhO)", "Type": COMP, "Subject": "Physics",
     "Tags": ["Applied Physics", "Astrophysics", "Pure Math / Theory"],
     "Link": "https://www.aapt.org/physicsteam/", "Is_Paid": False,
     "Description": "A series of physics exams from AAPT, starting with F=ma, that can lead to the U.S. team for the International Physics Olympiad."},

    # ---------------- Mathematics ----------------
    {"Title": "American Mathematics Competitions (AMC 10/12)", "Type": COMP, "Subject": "Mathematics",
     "Tags": ["Pure Math / Theory", "Applied Math / Modeling", "Problem Solving"],
     "Link": "https://maa.org/math-competitions", "Is_Paid": True,
     "Description": "The MAA's AMC 10 and AMC 12 exams, where high scorers can qualify for the AIME and the USA Mathematical Olympiad."},

    # ---------------- Earth & Environmental Science ----------------
    {"Title": "National Ocean Sciences Bowl", "Type": COMP, "Subject": "Earth & Environmental Science",
     "Tags": ["Marine Science", "Climate Science", "Sustainability"],
     "Link": "https://nosb.org", "Is_Paid": False,
     "Description": "A quiz-bowl-style academic competition on ocean science for high school teams, with regional bowls leading to a national finals."},
    {"Title": "Envirothon", "Type": COMP, "Subject": "Earth & Environmental Science",
     "Tags": ["Ecology", "Sustainability", "Geology"],
     "Link": "https://envirothon.org", "Is_Paid": False,
     "Description": "An environmental education competition where high school teams test their knowledge of areas like soils, aquatic ecology, forestry and wildlife."},

    # ---------------- Interdisciplinary STEM ----------------
    {"Title": "Regeneron International Science and Engineering Fair (ISEF)", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Research", "Design & Innovation", "Applied Physics"],
     "Link": "https://www.societyforscience.org/isef/", "Is_Paid": False,
     "Description": "The world's largest pre-college science fair, where finalists from affiliated regional and state fairs present original research across many categories."},
    {"Title": "Regeneron Science Talent Search", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Research", "Statistics & Data Analysis", "Design & Innovation"],
     "Link": "https://www.societyforscience.org/regeneron-sts/", "Is_Paid": False,
     "Description": "A long-running research competition for high school seniors, judged on an original independent research project."},
    {"Title": "Diamond Challenge", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Design & Innovation", "Entrepreneurship", "STEM Policy & Ethics"],
     "Link": "https://diamondchallenge.org", "Is_Paid": False,
     "Description": "A global entrepreneurship competition for high school student teams, run by the University of Delaware's Horn Entrepreneurship, where teams pitch business ideas and innovations."},
    {"Title": "Science Olympiad", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Teamwork", "Applied Physics", "Ecology"],
     "Link": "https://www.soinc.org", "Is_Paid": True,
     "Description": "A team competition with events across biology, chemistry, physics, earth science and engineering, from regional tournaments up to nationals."},
    {"Title": "Conrad Challenge", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Design & Innovation", "Entrepreneurship", "Aerospace"],
     "Link": "https://www.conradchallenge.org", "Is_Paid": True,
     "Description": "An innovation competition where student teams develop products and business plans that address real-world problems in areas like aerospace, energy and health."},
    {"Title": "DOE National Science Bowl", "Type": COMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Teamwork", "Applied Physics", "Problem Solving"],
     "Link": "https://science.osti.gov/wdts/nsb", "Is_Paid": False,
     "Description": "A fast-paced question-and-answer competition on science and math run by the U.S. Department of Energy, with regional events leading to a national finals."},
    {"Title": "MIT THINK", "Type": RESEARCH, "Subject": "Interdisciplinary STEM",
     "Tags": ["Research", "Design & Innovation", "Engineering Design"],
     "Link": "https://think.mit.edu", "Is_Paid": False,
     "Description": "A program where high school students propose a science or technology research project, with selected finalists getting mentoring from MIT students to carry it out."},
    {"Title": "Research Science Institute (RSI)", "Type": RESEARCH, "Subject": "Interdisciplinary STEM",
     "Tags": ["Research", "Statistics & Data Analysis", "Applied Physics"],
     "Link": "https://www.cee.org", "Is_Paid": False,
     "Description": "A highly selective summer research program for rising high school seniors, combining coursework with an independent research project mentored by scientists."},
    {"Title": "Summer Science Program (SSP)", "Type": RESEARCH, "Subject": "Interdisciplinary STEM",
     "Tags": ["Astrophysics", "Biochemistry", "Genetics", "Research"],
     "Link": "https://www.summerscience.org", "Is_Paid": True,
     "Description": "An intensive residential summer program where students work on a real research project in areas such as astrophysics, biochemistry and genomics."},
    {"Title": "COSMOS (California State Summer School for Mathematics and Science)", "Type": CAMP, "Subject": "Interdisciplinary STEM",
     "Tags": ["Robotics", "Marine Science", "Research"],
     "Link": "https://cosmos-ca.org", "Is_Paid": True,
     "Description": "A state-sponsored STEM summer school for grades 8 to 12 held on University of California campuses, with intensive courses in areas like robotics and marine biology."},
         {"Title": 'CyberPatriot National Youth Cyber Defense Competition', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Cybersecurity', 'Networking', 'Teamwork'],
     "Link": 'https://www.uscyberpatriot.org', "Is_Paid": False,
     "Description": 'A team-based cybersecurity competition in which students secure virtual computer systems and learn defensive cybersecurity skills.'},
    {"Title": 'picoCTF', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Cybersecurity', 'Capture the Flag', 'Programming'],
     "Link": 'https://picoctf.org', "Is_Paid": False,
     "Description": 'A cybersecurity learning competition built around capture-the-flag challenges that introduce cryptography, web security, forensics and related skills.'},
    {"Title": 'NCWIT Aspirations in Computing', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Women in Computing', 'Leadership', 'Technology'],
     "Link": 'https://www.aspirations.org', "Is_Paid": False,
     "Description": 'A recognition program honoring students for their computing interests, technical accomplishments and leadership.'},
    {"Title": 'Congressional Cybersecurity Challenge', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Cybersecurity', 'Problem Solving', 'Digital Safety'],
     "Link": 'https://www.congressionalcyberchallenge.com', "Is_Paid": False,
     "Description": 'A public cybersecurity challenge designed to encourage students and the public to explore cybersecurity concepts through hands-on activities.'},
    {"Title": 'MIT Beaver Works Summer Institute', "Type": CAMP, "Subject": 'Computer Science',
     "Tags": ['AI/Machine Learning', 'Robotics', 'Software Development'],
     "Link": 'https://beaverworks.ll.mit.edu/CMS/bw/bwsi', "Is_Paid": False,
     "Description": 'A summer program offering project-based courses in areas such as autonomous systems, machine learning and engineering for eligible high school students.'},
    {"Title": 'AI4ALL Summer Programs', "Type": CAMP, "Subject": 'Computer Science',
     "Tags": ['AI/Machine Learning', 'Ethical AI', 'Research'],
     "Link": 'https://ai-4-all.org', "Is_Paid": True,
     "Description": 'AI4ALL supports educational programs that introduce students to artificial intelligence, its applications and responsible development; offerings vary by partner and year.'},
    {"Title": 'Kode With Klossy', "Type": CAMP, "Subject": 'Computer Science',
     "Tags": ['Coding', 'Web Development', 'App Development'],
     "Link": 'https://www.kodewithklossy.com', "Is_Paid": False,
     "Description": 'A free coding camp program for eligible high school students, with curricula that have included web development, mobile apps and data science.'},
    {"Title": 'Hack Club', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Hackathons', 'Web Development', 'Open Source'],
     "Link": 'https://hackclub.com', "Is_Paid": False,
     "Description": 'A student-centered community that helps teens learn programming by building projects, joining events and sharing work with peers.'},
    {"Title": 'Technica Hackathon', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Hackathons', 'Software Development', 'Teamwork'],
     "Link": 'https://gotechnica.org', "Is_Paid": False,
     "Description": 'A student-run hackathon community focused on creating an inclusive environment for participants to build software and technology projects.'},
    {"Title": 'CyberStart America', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Cybersecurity', 'Digital Forensics', 'Logic'],
     "Link": 'https://cyberstartamerica.org', "Is_Paid": False,
     "Description": 'A cybersecurity learning and competition program that introduces students to practical cyber challenges and problem-solving.'},
    {"Title": 'American Computer Science League (ACSL)', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Algorithms', 'Programming', 'Computer Science Theory'],
     "Link": 'https://www.acsl.org', "Is_Paid": True,
     "Description": 'A computer science competition for school teams featuring topics such as programming, data structures, number systems and computer science theory.'},
    {"Title": 'US Cyber Challenge Cyber Quests', "Type": COMP, "Subject": 'Computer Science',
     "Tags": ['Cybersecurity', 'Networking', 'Digital Forensics'],
     "Link": 'https://www.uscyberchallenge.org', "Is_Paid": False,
     "Description": 'Cyber Quests are online challenges intended to help learners explore cybersecurity skills and identify areas for further study.'},
    {"Title": 'SeaPerch Challenge', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Underwater Robotics', 'Mechanical Design', 'Engineering Design'],
     "Link": 'https://seaperch.org', "Is_Paid": True,
     "Description": 'A robotics program in which student teams build and test remotely operated underwater vehicles and compete in engineering challenges.'},
    {"Title": 'MATE ROV Competition', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Underwater Robotics', 'Marine Science', 'Engineering Design'],
     "Link": 'https://materovcompetition.org', "Is_Paid": True,
     "Description": 'A remotely operated vehicle competition where student teams design, build and operate underwater robots for mission-based challenges.'},
    {"Title": 'eCYBERMISSION', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Engineering Design', 'Scientific Inquiry', 'Innovation'],
     "Link": 'https://www.ecybermission.com', "Is_Paid": False,
     "Description": 'A team STEM competition for students to investigate a community problem and propose a science- or engineering-based solution.'},
    {"Title": 'Future City Competition', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Civil Engineering', 'Sustainability', 'Urban Design'],
     "Link": 'https://futurecity.org', "Is_Paid": True,
     "Description": 'A project-based competition where middle school teams research, design and present a future city addressing an engineering challenge.'},
    {"Title": 'ExploraVision', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Technology Forecasting', 'Research', 'Innovation'],
     "Link": 'https://www.exploravision.org', "Is_Paid": False,
     "Description": 'A STEM competition where student teams imagine how an existing technology could develop in the future and explain the science behind their proposal.'},
    {"Title": 'NASA TechRise Student Challenge', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Aerospace', 'Experiment Design', 'Space Science'],
     "Link": 'https://www.nasa.gov/learning-resources/nasa-techrise-student-challenge/', "Is_Paid": False,
     "Description": 'A NASA challenge for student teams to design experiments for flight on a high-altitude balloon or other selected flight platform, depending on the current cycle.'},
    {"Title": 'Samsung Solve for Tomorrow', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Design & Innovation', 'Engineering Design', 'Community Impact'],
     "Link": 'https://www.samsung.com/us/solvefortomorrow/', "Is_Paid": False,
     "Description": 'A school-based competition encouraging students to apply STEM skills to a local community issue through a proposed solution.'},
    {"Title": 'FIRST Tech Challenge', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Robotics', 'Programming', 'Mechanical Design'],
     "Link": 'https://www.firstinspires.org/robotics/ftc', "Is_Paid": True,
     "Description": 'A team robotics competition where students design, build and program robots to complete a new challenge each season.'},
    {"Title": 'FIRST LEGO League Challenge', "Type": COMP, "Subject": 'Engineering',
     "Tags": ['Robotics', 'Coding', 'Engineering Design'],
     "Link": 'https://www.firstinspires.org/robotics/fll', "Is_Paid": True,
    }
]


def check_link(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code
    except requests.RequestException:
        return None


def run():
    added = 0
    print(f"Adding up to {len(PROGRAMS)} curated programs...\n")
    for p in PROGRAMS:
        title = p["Title"]
        try:
            existing = supabase.table("Opportunities").select("Title").eq("Title", title).execute()
            if existing.data:
                print(f"⏭️  Already in database: {title}")
                continue
            payload = dict(p)
            payload["Deadline"] = "TBD"
            supabase.table("Opportunities").insert(payload).execute()
            print(f"✅ Added: {title}")
            added += 1
        except Exception as e:
            print(f"⚠️  Error adding '{title}': {e}")

    print(f"\nAdded {added} programs.\n")
    print("🔗 Checking links (a 403 usually just means the site blocks scripts, not that it's broken)...")
    for p in PROGRAMS:
        status = check_link(p["Link"])
        flag = "OK " if status and status < 400 else "CHECK"
        print(f"   [{flag}] {status}  {p['Title']}  ->  {p['Link']}")


if __name__ == "__main__":
    run()