import re

# ===============================
# MASTER SKILL TAXONOMY (ROBUST)
# ===============================
SKILL_TAXONOMY = {

    # ---------- SOFTWARE / IT ----------
    "python", "java", "javascript", "typescript",
    "c", "c++", "c#", "go",
    "ruby", "php", "swift", "kotlin", "scala", "r",

    "html", "css", "sass", "bootstrap", "tailwind css",
    "react", "angular", "vue.js", "next.js", "node.js",
    "express.js", "django", "flask", "spring boot",

    "rest api", "graphql", "microservices",
    "git", "github", "gitlab", "bitbucket",

    # ---------- CLOUD / DEVOPS ----------
    "aws", "azure", "gcp",
    "docker", "kubernetes", "terraform",
    "jenkins", "ci cd", "ansible",
    "linux", "bash", "shell scripting",

    # ---------- DATA / AI ----------
    "data analysis", "data science", "machine learning",
    "deep learning", "artificial intelligence",
    "nlp", "computer vision",

    "pandas", "numpy", "scikit learn",
    "tensorflow", "pytorch", "keras",
    "power bi", "tableau", "excel",

    "spark", "hadoop", "airflow", "kafka",

    # ---------- DATABASES ----------
    "sql", "mysql", "postgresql", "oracle",
    "mongodb", "cassandra", "redis", "dynamodb",

    # ---------- CYBERSECURITY ----------
    "cyber security", "information security",
    "network security", "penetration testing",
    "ethical hacking", "risk assessment",

    # ---------- BUSINESS / MANAGEMENT ----------
    "business analysis", "requirements gathering",
    "stakeholder management", "process improvement",
    "project management", "program management",
    "product management",

    "agile", "scrum", "kanban", "waterfall",

    # ---------- FINANCE / ACCOUNTING ----------
    "financial analysis", "accounting",
    "budgeting", "forecasting",
    "risk management", "taxation",
    "auditing",

    # ---------- MARKETING / SALES ----------
    "digital marketing", "seo", "sem",
    "content marketing", "email marketing",
    "social media marketing",
    "sales", "business development",
    "lead generation", "crm",

    # ---------- HR / OPERATIONS ----------
    "recruitment", "talent acquisition",
    "payroll", "hr operations",
    "employee engagement",
    "performance management",

    "operations management",
    "supply chain management",
    "logistics",

    # ---------- HEALTHCARE ----------
    "clinical research", "patient care",
    "medical coding", "healthcare administration",

    # ---------- EDUCATION ----------
    "teaching", "curriculum development",
    "instructional design",
    "training and development",

    # ---------- DESIGN ----------
    "ui design", "ux design",
    "figma", "adobe photoshop",
    "adobe illustrator",

    # ---------- SOFT SKILLS (CONTROLLED) ----------
    "communication", "leadership",
    "problem solving", "critical thinking",
    "time management", "team collaboration"
}

# ===============================
# ALIASES
# ===============================
SKILL_ALIASES = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "js": "javascript",
    "reactjs": "react",
    "node": "node.js",
    "tf": "tensorflow",
    "ci/cd": "ci cd",
    "spring-boot": "spring boot",
    "scikit-learn": "scikit learn",
    "fp&a": "financial analysis",
    "seo/sem": "seo",
    "pm": "project management",
    "ba": "business analysis"
}

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("-", " ").replace("_", " ")
    text = text.replace(".", ".")  # keep dots for js frameworks
    return text

def extract_resume_skills(text: str) -> list:
    """
    Enterprise-grade, role-agnostic skill extraction
    """
    text = normalize_text(text)
    found = set()

    # Apply aliases first
    for alias, canonical in SKILL_ALIASES.items():
        text = re.sub(rf"(?<!\w){re.escape(alias)}(?!\w)", canonical, text)

    for skill in SKILL_TAXONOMY:
        skill_tokens = skill.split()
        pattern = r"\b" + r"\s+".join(map(re.escape, skill_tokens)) + r"\b"
        if re.search(pattern, text):
            found.add(skill)

    return sorted(found)
