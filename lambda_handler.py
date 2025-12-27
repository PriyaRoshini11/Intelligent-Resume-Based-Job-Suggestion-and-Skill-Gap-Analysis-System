# lambda_handler.py
import os
import json
import time
import re
import traceback
import requests
import hashlib
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Helper function for UTC time
def get_utc_now():
    return datetime.now(timezone.utc)

# Configuration
MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ.get("MONGO_DB", "resume_db")
S3_BUCKET = os.environ.get("S3_BUCKET")
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "in")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
MAX_JOB_PAGES = int(os.environ.get("MAX_JOB_PAGES", "2"))
MAX_JOB_PAGES = min(MAX_JOB_PAGES, 2)
MAX_JOBS_PER_QUERY = 10
MAX_TOTAL_JOBS = 800

_mongo_client = None

def get_mongo_client():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=30000,
            maxPoolSize=10
        )
    return _mongo_client

db = get_mongo_client()[MONGO_DB]
jobs_col = db["jobs"]

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

def extract_skills_from_text(text: str) -> list:
    """
    Enterprise-grade, role-agnostic skill extraction
    """
    text = normalize_text(text)
    found = set()

    # Apply aliases first
    for alias, canonical in SKILL_ALIASES.items():
        text = re.sub(rf"(?<!\w){re.escape(alias)}(?!\w)", canonical, text)

    for skill in SKILL_TAXONOMY:
        pattern = rf"(?<!\w){re.escape(skill)}(?!\w)"
        if re.search(pattern, text):
            found.add(skill)

    return sorted(found)

_thread_local = threading.local()

def get_http_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session()
    return _thread_local.session

def fetch_adzuna(page=1, query="software engineer", country="in"):
    """Fetch from Adzuna API"""
    try:
        time.sleep(0.5)

        if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
            print("Adzuna credentials missing")
            return []
        
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 10,
            "what": query,
            "content-type": "application/json"
        }
        
        session = get_http_session()
        response = session.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data.get("results", [])
        
    except Exception as e:
        print(f"Adzuna error for query '{query}': {e}")
        return []

def fetch_jsearch(page=1, query="software engineer"):
    """Fetch from JSearch API"""
    if not RAPIDAPI_KEY:
        print("RapidAPI key missing")
        return []
    
    try:
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        params = {
            "query": query,
            "page": page,
            "num_pages": 1,
            "country": "us"
        }
        
        session = get_http_session()
        response = session.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data.get("data", [])
        
    except Exception as e:
        print(f"JSearch error for query '{query}': {e}")
        return []

def normalize_job(raw_job, source):
    """Normalize job data with enhanced processing"""
    try:
        title = ""
        company = ""
        description = ""
        location = ""
        posted_date = None
        
        if source == "adzuna":
            title = raw_job.get("title", "")
            company_obj = raw_job.get("company", {})
            company = company_obj.get("display_name", "") if isinstance(company_obj, dict) else str(company_obj)
            description = raw_job.get("description", "")
            location_obj = raw_job.get("location", {})
            location = location_obj.get("display_name", "") if isinstance(location_obj, dict) else str(location_obj)
            
            posted_date_str = raw_job.get("created", "")
            if posted_date_str:
                try:
                    from dateutil import parser
                    posted_date = parser.parse(posted_date_str)
                except:
                    posted_date = None
            
        elif source == "jsearch":
            title = raw_job.get("job_title", "")
            company = raw_job.get("employer_name", "")
            description = raw_job.get("job_description", "")
            location = f"{raw_job.get('job_city', '')}, {raw_job.get('job_country', '')}"
            
            posted_date_str = raw_job.get("job_posted_at_datetime_utc", "")
            if posted_date_str:
                try:
                    from dateutil import parser
                    posted_date = parser.parse(posted_date_str)
                except:
                    posted_date = None
        
        # Clean and validate fields
        title = str(title)[:200].strip()
        if not title:
            title = "Software Developer"
        
        company = str(company)[:100].strip()
        if not company:
            company = "Technology Company"
        
        # Clean description
        if description:
            import re
            # Remove HTML tags
            description = re.sub(r'<[^>]+>', ' ', description)
            # Remove excessive whitespace
            description = re.sub(r'\s+', ' ', description)
            # Limit length
            description = description[:2000]
        else:
            description = f"{title} position requiring relevant skills and experience."
        
        location = str(location)[:150].strip()
        if not location:
            location = "Remote"
        
        if posted_date and posted_date.tzinfo is None:
            posted_date = posted_date.replace(tzinfo=timezone.utc)

        job_text_for_skills = f"{title} {description}"
        job_skills = extract_skills_from_text(job_text_for_skills)
        
        # Create job document with enhanced fields
        normalized = {
            "job_id": None,
            "title": title,
            "company": company,
            "description": description,
            "location": location,
            "posted_date": posted_date,
            "skills": job_skills,
            "source": source,
            "ingested_at": get_utc_now(),
            "embedding": None,
            "embedded_at": None,
            "last_updated": get_utc_now(),
            "active": True,
            "job_type": "Full-time",  # Default
            "experience_level": "Mid",  # Default
            "remote": "Remote" in location or "remote" in location.lower()
        }
        
        # Detect job type and experience level from title
        title_lower = title.lower()
        
        # Job type detection
        if any(word in title_lower for word in ['contract', 'freelance', 'consultant']):
            normalized["job_type"] = "Contract"
        elif any(word in title_lower for word in ['part-time', 'part time']):
            normalized["job_type"] = "Part-time"
        elif any(word in title_lower for word in ['intern', 'internship']):
            normalized["job_type"] = "Internship"
        
        # Experience level detection
        if any(word in title_lower for word in ['senior', 'lead', 'principal', 'manager', 'director']):
            normalized["experience_level"] = "Senior"
        elif any(word in title_lower for word in ['junior', 'entry', 'associate', 'trainee']):
            normalized["experience_level"] = "Entry"
        elif any(word in title_lower for word in ['mid', 'intermediate']):
            normalized["experience_level"] = "Mid"
        
        # Generate hash for deduplication
        hash_string = f"{title}|{company}|{location}"
        job_hash = hashlib.md5(hash_string.encode()).hexdigest()
        normalized["job_hash"] = job_hash
        normalized["job_id"] = job_hash
        
        return normalized
        
    except Exception as e:
        print(f"Normalization error: {e}")
        return None
    
def fetch_jobs_for_query(query):
    results = []

    for page in range(1, MAX_JOB_PAGES + 1):
        for j in fetch_adzuna(page, query,ADZUNA_COUNTRY):
            job = normalize_job(j, "adzuna")
            if job:
                results.append(job)
                if len(results) >= MAX_JOBS_PER_QUERY:
                    return results

        for j in fetch_jsearch(page, query):
            job = normalize_job(j, "jsearch")
            if job:
                results.append(job)
                if len(results) >= MAX_JOBS_PER_QUERY:
                    return results

    return results


def lambda_handler(event, context):
    """Main Lambda handler with comprehensive job fetching"""
    print(f"Lambda started at {get_utc_now().isoformat()}")
    

    try:
        # Comprehensive job queries covering all tech domains
        job_queries = [

            # ===============================
            # SOFTWARE / IT
            # ===============================
            "software engineer", "software developer", "full stack developer",
            "backend developer", "frontend developer", "web developer",
            "java developer", "python developer", "dotnet developer",

            # ===============================
            # DATA / AI / ML
            # ===============================
            "data scientist", "machine learning engineer", "ai engineer",
            "data analyst", "data engineer", "business intelligence analyst",
            "nlp engineer", "computer vision engineer",

            # ===============================
            # CLOUD / DEVOPS
            # ===============================
            "devops engineer", "cloud engineer", "site reliability engineer",
            "aws engineer", "azure engineer", "gcp engineer", "cloud architect",

            # ===============================
            # CYBERSECURITY
            # ===============================
            "cybersecurity analyst", "security engineer",
            "information security analyst", "penetration tester",

            # ===============================
            # MOBILE DEVELOPMENT
            # ===============================
            "android developer", "ios developer", "mobile app developer",
            "react native developer", "flutter developer",

            # ===============================
            # DATABASE / DATA PLATFORM
            # ===============================
            "database administrator", "sql developer", "mongodb developer",
            "data architect", "database engineer",

            # ===============================
            # QA / TESTING
            # ===============================
            "qa engineer", "test engineer", "automation tester",
            "quality assurance analyst", "software tester",

            # ===============================
            # IT MANAGEMENT
            # ===============================
            "technical lead", "engineering manager", "software architect",
            "product manager", "project manager",

            # ===============================
            # BUSINESS / CORPORATE
            # ===============================
            "business analyst", "operations manager", "process analyst",
            "operations executive", "program coordinator",

            # ===============================
            # HR / TALENT
            # ===============================
            "hr executive", "hr manager", "talent acquisition specialist",
            "recruiter", "hr business partner",

            # ===============================
            # FINANCE / ACCOUNTING
            # ===============================
            "financial analyst", "accountant", "finance executive",
            "auditor", "risk analyst",

            # ===============================
            # MARKETING / SALES
            # ===============================
            "digital marketing executive", "seo specialist",
            "marketing analyst", "content marketing manager",
            "sales executive", "business development executive",

            # ===============================
            # DESIGN / CREATIVE
            # ===============================
            "ui ux designer", "graphic designer",
            "product designer", "visual designer",

            # ===============================
            # HEALTHCARE
            # ===============================
            "healthcare analyst", "clinical coordinator",
            "medical coder", "hospital administrator",

            # ===============================
            # EDUCATION / TRAINING
            # ===============================
            "technical trainer", "data science trainer",
            "lecturer", "assistant professor", "faculty",

            # ===============================
            # CORE ENGINEERING (NON-IT)
            # ===============================
            "mechanical engineer", "civil engineer",
            "electrical engineer", "electronics engineer",
            "manufacturing engineer",

            # ===============================
            # OPERATIONS / SUPPLY CHAIN
            # ===============================
            "operations analyst", "supply chain analyst",
            "logistics executive", "procurement executive"
        ]
        
        job_queries = job_queries[:20]

        all_jobs = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(fetch_jobs_for_query, q) for q in job_queries]
            for f in as_completed(futures):
                if len(all_jobs) >= MAX_TOTAL_JOBS:
                    break
                all_jobs.extend(f.result())

        print(f"[INFO] Total jobs fetched: {len(all_jobs)}")

# =====================================================
# 5️⃣ UPSERT JOBS INTO MONGODB
# =====================================================
        for job in all_jobs:
            jobs_col.update_one(
                {"job_hash": job["job_hash"]},
                {"$set": job},
                upsert=True
            )

            # Reload active jobs AFTER insert
        db_jobs = list(jobs_col.find({"active": True}).limit(1500))
        print(f"[INFO] Active jobs in DB: {len(db_jobs)}")

# =====================================================
# 8️⃣ INSERT MATCHES
# =====================================================

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "jobs_fetched",
                "jobs_fetched": len(all_jobs)
            })
        }
    
    except Exception as e:
        # ===============================
        # ❌ ERROR HANDLING (MANDATORY)
        # ===============================
        print("❌ Lambda execution failed")
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "error",
                "message": str(e)[:500],
                "timestamp": get_utc_now().isoformat()
            })
        }