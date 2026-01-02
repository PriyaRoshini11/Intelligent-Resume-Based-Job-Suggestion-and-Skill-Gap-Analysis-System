# streamlit_app.py
import os
import json
import time
import requests
import streamlit as st
import boto3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import defaultdict

# =========================
# ENV & CONFIG
# =========================
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "resume_db")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_UPLOAD_PREFIX = os.getenv("S3_UPLOAD_PREFIX", "uploads/")
LAMBDA_INVOKE_URL = os.getenv("LAMBDA_INVOKE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

TOP_K = 20  # Documentation requirement

# =========================
# CLIENTS
# =========================
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
s3 = boto3.client("s3")

# =========================
# IMPORT UTILITIES
# =========================
from utils.extractor import extract_text_from_pdf_bytes, extract_text_from_docx_bytes
from utils.enhanced_extractor import extract_resume_skills
from utils.embedder import sentence_embed_texts
from utils.ranker import cos_sim_safe
from utils.agentic_openai import generate_ai_explanation
from utils.coursera_api import coursera_search

# =========================
# HELPERS
# =========================
def utc_now():
    return datetime.now(timezone.utc)

def validate_file(file_bytes, filename):
    if len(file_bytes) > 10 * 1024 * 1024:
        return False, "File too large (max 10MB)"
    if not filename.lower().endswith((".pdf", ".docx")):
        return False, "Only PDF or DOCX allowed"
    return True, "OK"

def daily_refresh():
    """
    Auto-invoke Lambda once per 24 hours (SAFE + IDENTITY-AWARE)
    """
    if "daily_refresh_done" in st.session_state:
        return  # prevent multiple calls per session

    meta = db.meta.find_one({"_id": "last_refresh"})
    now = utc_now()

    last_time = meta.get("time") if meta else None

    if last_time:
        # 🔧 FIX: normalize MongoDB datetime to UTC
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        if now - last_time < timedelta(days=1):
            st.session_state["daily_refresh_done"] = True
            return

    if not LAMBDA_INVOKE_URL:
        st.session_state["daily_refresh_done"] = True
        return

    try:
        resp = requests.post(
            LAMBDA_INVOKE_URL,
            json={"source": "streamlit_daily_refresh"},
            timeout=120
        )

        if resp.status_code == 200:
            db.meta.update_one(
                {"_id": "last_refresh"},
                {"$set": {"time": now}},
                upsert=True
            )
            st.info("🔄 Daily job refresh completed")
        else:
            st.warning(f"⚠️ Daily refresh skipped (HTTP {resp.status_code})")

    except Exception as e:
        # DO NOT fail UI
        st.warning("⚠️ Daily refresh skipped")

    finally:
        st.session_state["daily_refresh_done"] = True

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(
    page_title="Smart Job Matcher",
    layout="wide"
)

st.title("🧠 Intelligent Resume-Based Job Suggestion System")
st.caption("Explainable job matching with skill-gap analysis")

# Trigger daily refresh
daily_refresh()

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("⚙️ Configuration")
    user_id = st.text_input("User ID", value="user_001")

    st.divider()
    st.header("🗄️ Database Maintenance")

    if st.button("🧹 Clear DB"):
        jobs_deleted = db.jobs.delete_many({}).deleted_count
        db.resumes.delete_many({"user_id": user_id})
        st.success("✅ Database cleared")

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📄 Upload Resume", "🔄 Fetch Jobs", "🎯 Find Matches"])

# =========================
# TAB 1: UPLOAD RESUME
# =========================
with tab1:
    st.header("📄 Upload Resume")

    uploaded = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

    if uploaded:
        file_bytes = uploaded.getvalue()
        valid, msg = validate_file(file_bytes, uploaded.name)
        if not valid:
            st.error(msg)
            st.stop()

        if st.button("🚀 Process Resume"):
            with st.spinner("Processing resume..."):
                text = (
                    extract_text_from_pdf_bytes(file_bytes)
                    if uploaded.name.lower().endswith(".pdf")
                    else extract_text_from_docx_bytes(file_bytes)
                )

                skills = extract_resume_skills(text)
                embedding = sentence_embed_texts([text], normalize=True)[0]

                db.resumes.delete_many({"user_id": user_id})
                db.resumes.insert_one({
                    "user_id": user_id,
                    "text": text,
                    "skills": skills,
                    "embedding": embedding,
                    "uploaded_at": utc_now()
                })

                s3.put_object(
                    Bucket=S3_BUCKET,
                    Key=f"{S3_UPLOAD_PREFIX}{user_id}/{int(time.time())}_{uploaded.name}",
                    Body=file_bytes
                )

                st.success("✅ Resume uploaded")
                st.write("**Extracted Skills:**", ", ".join(skills))

# =========================
# TAB 2: FETCH JOBS
# =========================
with tab2:
    st.header("🔄 Fetch Jobs")

    if st.button("📥 Fetch Jobs Now"):
        if not LAMBDA_INVOKE_URL:
            st.error("Lambda URL not configured")
        else:
            requests.post(LAMBDA_INVOKE_URL, timeout=60)
            st.success("Jobs fetch triggered")

    st.metric("Active Jobs", db.jobs.count_documents({"active": True}))

# =========================
# TAB 3: FIND MATCHES
# =========================
with tab3:
    st.header("🎯 Top Job Matches")

    if st.button("🔍 Find Matches"):
        resume = db.resumes.find_one(
            {"user_id": user_id},
            sort=[("uploaded_at", -1)]
        )

        if not resume:
            st.error("Upload resume first")
            st.stop()

        resume_skills = resume["skills"]
        resume_vec = np.array(resume["embedding"], dtype=float)

        jobs = list(db.jobs.find({"active": True}))
        results = []

        for job in jobs:
            job_skills = job.get("skills", [])
            job_text = f"{job.get('title','')} {job.get('description','')}"

            if not job.get("embedding"):
                job_vec = sentence_embed_texts([job_text], normalize=True)[0]
                db.jobs.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"embedding": job_vec}}
                )
            else:
                job_vec = job["embedding"]

            semantic = cos_sim_safe(resume_vec, job_vec)
            keyword = len(set(resume_skills) & set(job_skills)) / max(1, len(resume_skills))

            # -------- FIXED PART --------
            recency = 0.5
            posted_date = job.get("posted_date")
            if posted_date:
                try:
                    if isinstance(posted_date, str):
                        from dateutil import parser
                        posted_date = parser.parse(posted_date)
                    days_old = (utc_now() - posted_date).days
                    recency = 1.0 if days_old <= 1 else 0.8 if days_old <= 7 else 0.6 if days_old <= 30 else 0.3
                except:
                    recency = 0.5

            popularity = 0.5  # neutral (salary not used)

            final_score = (
                0.55 * semantic +
                0.25 * keyword +
                0.10 * recency +
                0.10 * popularity
            )
            # --------------------------------

            missing = sorted(set(job_skills) - set(resume_skills))

            results.append({
                "job": job,
                "score": final_score,
                "semantic": semantic,
                "keyword": keyword,
                "missing": missing
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        top = results[:TOP_K]

        st.success(f"✅ Showing top {len(top)} matches")

        # =========================
        # DISPLAY JOBS (FINAL)
        # =========================
        for i, r in enumerate(top, 1):
            job = r["job"]

            st.markdown("---")
            source = job.get("source", "unknown").lower()

            if source == "adzuna":
                badge = "🟢 Adzuna"
            elif source == "jsearch":
                badge = "🔵 JSearch"
            else:
                badge = "⚪ Unknown"

            st.subheader(
                f"{i}. {job.get('title')} — {job.get('company','')}  \n"
                f"**Score:** `{r['score']:.3f}` | {badge}"
            )
            st.markdown(f"### ⭐ Match Score: `{r['score']:.3f}`")

            # ---- Job Details ----
            st.markdown("**Job Details:**")
            st.write(
                f"- 📍 Location: {job.get('location', 'Not available')}\n"
                f"- 🗓 Posted Date: {job.get('posted_date', 'Not available')}\n"
                f"- 💼 Job Type: {job.get('job_type', 'Not specified')}\n"
                f"- 🎓 Experience Level: {job.get('experience_level', 'Not specified')}"
            )

            # ---- AI Explanation ----
            explanation = generate_ai_explanation(
                OPENAI_API_KEY,
                job.get("title",""),
                job.get("description",""),
                resume_skills,
                job.get("skills", []),
                r["missing"]
            )
            st.info(explanation)

            # ---- Required Skills ----
            st.markdown("**Required Skills:**")
            if job.get("skills"):
                st.write(", ".join(job["skills"]))
            else:
                st.caption("Not available")

            # ---- Missing Skills + Coursera ----
            st.markdown("**Missing Skills & Recommended Courses:**")
            if not r["missing"]:
                st.success("✅ No major skill gaps detected")
            else:
                for skill in r["missing"][:5]:
                    st.write(f"- {skill}")
                    courses = coursera_search(skill, limit=1)
                    if courses:
                        st.caption(f"📘 {courses[0]['title']} — {courses[0]['url']}")


        # =========================
        # SKILL GAP HEATMAP
        # =========================
        st.subheader("Skill-gap Heat Map:")
        role_skill_map = defaultdict(set)
        for r in top:
            role = r["job"]["title"]
            for skill in r["missing"]:
                role_skill_map[role].add(skill)

        roles = list(role_skill_map.keys())[:10]
        skills = sorted({s for v in role_skill_map.values() for s in v})

        heatmap = [
            [1 if skill in role_skill_map[role] else 0 for skill in skills]
            for role in roles
        ]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.imshow(heatmap, cmap="Reds", aspect="auto")
        ax.set_xticks(range(len(skills)))
        ax.set_xticklabels(skills, rotation=45, ha="right")
        ax.set_yticks(range(len(roles)))
        ax.set_yticklabels(roles)
        ax.set_title("Skill Gap Heatmap")
        st.pyplot(fig)
# =========================
# MOST COMMON MISSING SKILLS
# =========================
        st.subheader("Most Common Missing Skills")

        all_missing = [skill for r in top for skill in r["missing"]]

        if all_missing:
            freq = pd.Series(all_missing).value_counts().head(10)

            fig, ax = plt.subplots(figsize=(10, 4))
            freq.plot(kind="barh", ax=ax, color="#4A90E2")
            ax.invert_yaxis()
            ax.set_xlabel("Count")
            ax.set_ylabel("Skill")
            ax.set_title("Most Common Missing Skills Across Top Jobs")

            st.pyplot(fig)
        else:
            st.info("No missing skills detected in top matches.")

# =========================
# FOOTER
# =========================
st.divider()
st.caption("✔ Documentation-compliant | ✔ Explainable AI | ✔ Skill-gap visualization")
