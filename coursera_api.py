# utils/coursera_api.py
import requests
from urllib.parse import quote_plus

# ======================================================
# PUBLIC ENTRY POINT
# ======================================================
def coursera_search(skill: str, limit: int = 3):
    """
    Return Coursera course recommendations for a given skill.
    Priority:
    1. Coursera public catalog API
    2. Curated skill-to-course mappings (IT + NON-IT)
    3. Generic Coursera search fallback
    """
    if not skill or len(skill.strip()) < 2:
        return [{
            "title": "Search Coursera",
            "url": "https://www.coursera.org",
            "description": "Browse Coursera courses"
        }]

    skill_clean = skill.lower().strip()
    search_query = quote_plus(skill_clean)

    # Strategy 1: Coursera API
    courses = try_coursera_api(search_query, limit)
    if courses:
        return courses[:limit]

    # Strategy 2: Curated mappings (IT + NON-IT)
    courses = try_skill_mapping(skill_clean, limit)
    if courses:
        return courses[:limit]

    # Strategy 3: Generic fallback
    return get_fallback_courses(skill_clean)


# ======================================================
# STRATEGY 1 — COURSES API
# ======================================================
def try_coursera_api(search_query: str, limit: int):
    try:
        url = (
            "https://api.coursera.org/api/courses.v1"
            f"?q=search&query={search_query}&limit={limit}"
            "&fields=slug,name,description"
        )

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []

        elements = response.json().get("elements", [])
        courses = []

        for course in elements:
            title = course.get("name")
            slug = course.get("slug")
            if title and slug:
                desc = course.get("description", "")
                courses.append({
                    "title": title,
                    "url": f"https://www.coursera.org/learn/{slug}",
                    "description": desc[:120] + "..." if desc else f"Course on {search_query.replace('+', ' ')}",
                    "source": "Coursera API"
                })

        return courses

    except Exception:
        return []


# ======================================================
# STRATEGY 2 — CURATED SKILL MAPPINGS (IT + NON-IT)
# ======================================================
def try_skill_mapping(skill_clean: str, limit: int):
    """
    Curated, domain-level mappings.
    Covers IT and NON-IT roles without overfitting.
    """
    skill_course_map = {

        # ---------- IT / SOFTWARE ----------
        "python": [
            ("Python for Everybody", "python"),
            ("Python Data Structures", "python-data")
        ],
        "javascript": [
            ("JavaScript for Web Development", "javascript"),
            ("Full-Stack Web Development", "full-stack")
        ],
        "react": [
            ("Front-End Web Development with React", "front-end-react"),
            ("React Basics", "react-basics")
        ],
        "sql": [
            ("SQL for Data Science", "sql-for-data-science"),
            ("Databases and SQL", "databases-sql")
        ],

        # ---------- DATA / AI ----------
        "machine learning": [
            ("Machine Learning", "machine-learning"),
            ("Applied Data Science with Python", "applied-data-science")
        ],
        "data science": [
            ("Data Science Fundamentals", "data-science"),
            ("Data Analysis with Python", "data-analysis-python")
        ],

        # ---------- CLOUD / DEVOPS ----------
        "aws": [
            ("AWS Fundamentals", "aws-fundamentals"),
            ("AWS Cloud Technical Essentials", "aws-cloud")
        ],
        "docker": [
            ("Docker for Beginners", "docker"),
            ("Introduction to Containers", "containers")
        ],
        "kubernetes": [
            ("Architecting with Google Kubernetes Engine", "architecting-gcp-kubernetes"),
        ],

        # ---------- BUSINESS / MANAGEMENT ----------
        "project management": [
            ("Google Project Management", "google-project-management"),
            ("Project Management Principles", "project-management-principles")
        ],
        "business analysis": [
            ("Business Analysis Fundamentals", "business-analysis"),
            ("Requirements Gathering", "requirements-gathering")
        ],

        # ---------- HR ----------
        "recruitment": [
            ("Recruiting, Hiring and Onboarding Employees", "recruiting-hiring"),
            ("Human Resource Management", "human-resource-management")
        ],
        "talent acquisition": [
            ("Talent Management", "talent-management")
        ],

        # ---------- FINANCE ----------
        "financial analysis": [
            ("Financial Analysis Fundamentals", "financial-analysis"),
            ("Corporate Finance Essentials", "corporate-finance")
        ],
        "accounting": [
            ("Financial Accounting Fundamentals", "financial-accounting"),
            ("Managerial Accounting", "managerial-accounting")
        ],

        # ---------- MARKETING ----------
        "digital marketing": [
            ("Digital Marketing Specialization", "digital-marketing"),
            ("SEO Fundamentals", "seo-fundamentals")
        ],
        "seo": [
            ("Search Engine Optimization", "seo")
        ]
    }

    for key, courses in skill_course_map.items():
        if key in skill_clean:
            return [
                {
                    "title": title,
                    "url": f"https://www.coursera.org/learn/{slug}",
                    "description": f"Learn {key}",
                    "source": "Curated Mapping"
                }
                for title, slug in courses[:limit]
            ]

    return []


# ======================================================
# STRATEGY 3 — GENERIC FALLBACK
# ======================================================
def get_fallback_courses(skill_clean: str):
    """
    Safe fallback when no curated mapping exists.
    """
    return [{
        "title": f"Search Coursera for '{skill_clean.title()}'",
        "url": f"https://www.coursera.org/search?query={quote_plus(skill_clean)}",
        "description": f"Browse Coursera courses related to {skill_clean}",
        "source": "Coursera Search"
    }]
