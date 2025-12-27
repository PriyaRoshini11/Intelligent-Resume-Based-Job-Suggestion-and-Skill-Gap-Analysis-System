# Intelligent-Resume-Based-Job-Suggestion-and-Skill-Gap-Analysis-System

**📌 Problem Statement:**

Organizations and job seekers struggle to match resumes with the most relevant job opportunities. Traditional job searches rely heavily on keyword filters, which fail to capture deeper semantic meaning or candidate skills.

This project solves that by building an AI-powered Resume → Job Matching platform that analyzes resumes, fetches real job listings, computes semantic similarity, detects skill gaps, and ranks job opportunities using a multi-factor scoring system.

**🌍 Domain:**

Artificial Intelligence | Cloud Computing | Data Engineering | Natural Language Processing

**🎯 Key Objectives:**

✔ Extract text & skills from uploaded resumes

✔ Fetch real job data via APIs (Adzuna / JSearch)

✔ Generate semantic embeddings using Sentence Transformers

✔ Rank jobs using a weighted scoring formula

✔ Provide intelligent explanations using LLM (GPT-4o-mini)

✔ Detect missing skills → Recommend Coursera courses

✔ Display results through an interactive Streamlit UI

✔ Automate job fetching using AWS Lambda + S3 trigger

✔ Store results in MongoDB

**🧠 Skills Gained:**

Resume Parsing (PDF/DOCX)

Embedding Techniques (Sentence Transformers)

Job Ranking Algorithms

LLM-based reasoning and explanation generation

AWS Lambda event-driven architecture

API Integration (JSearch/Adzuna)

Streamlit UI development

MongoDB schema design

Cloud data pipelines

Skill-gap analysis & similarity scoring

**🧩 Architecture Overview:**

**✔ Frontend (Streamlit App)**

Upload resume

Resume is stored in S3. Job ingestion Lambda is triggered via HTTP (Streamlit daily refresh or manual fetch).

Fetches stored jobs from MongoDB

Computes embeddings locally

Ranks job matches

Calls LLM for explanations (optional)

Visualizes skill gaps & recommends courses

Provides Fetch jobs → triggers Lambda via HTTP

**✔ Backend (AWS Lambda)**

Triggered via HTTP endpoint (manual fetch or daily refresh from Streamlit).

Lambda tasks:

Fetch multiple job categories (Data Scientist, Software Engineer, Cloud, ML Engineer...)

Normalize raw job records

Add realistic fallback values ( posted_date)

Deduplicate using a job hash

Store into MongoDB:

jobs collection

Lambda does NOT compute embeddings — Streamlit does it on demand (faster, cheaper).

Matching and embedding computation are intentionally handled in Streamlit to reduce Lambda execution time, cost, and cold-start overhead.

**✔ Database (MongoDB Cloud)**

Collections:

| Collection | Purpose                                                        |
| ---------- | -------------------------------------------------------------- |
| `resumes`  | Store resume text, metadata                                    |
| `jobs`     | Raw job descriptions fetched by Lambda                         |

**🤖 AI / ML Components:**

🧩 1. Sentence Transformers Embedding

Used model: all-MiniLM-L6-v2

Fast

Lightweight

Free & offline

Perfect for similarity scoring

🧩 2. Job Ranking Formula

final_score = 0.55 * semantic_similarity + 0.25 * keyword_overlap + 0.10 * recency_weight + 0.10 * popularity_score

Note: Popularity score is currently set to a neutral constant (0.5) due to lack of reliable salary/applicant count data from free job APIs.

🧩 3. LLM Reasoning

Uses OpenAI GPT-4o-mini via API key to generate:

✔ Why this job matches

✔ Missing skills

✔ Personalized recommendations

**🖥 Technologies Used:**

| **Category**              | **Tools / Technologies**                                                   |
| ------------------------- | -------------------------------------------------------------------------- |
| **Programming**           | Python                                                                     |
| **NLP**                   | Sentence Transformers (all-MiniLM-L6-v2), Regex-based parsing              |
| **AI Reasoning**          | OpenAI GPT-4o-mini (LLM explanations, missing skill generation)            |
| **Backend**               | AWS S3 (resume uploads), AWS Lambda (job ingestion), AWS CloudWatch        |
| **Database**              | MongoDB (resumes, jobs)                                                    |
| **Deployment / UI**       | Streamlit                                                                  |
| **APIs Used**             | JSearch API / Adzuna API (job fetching), Coursera API (course suggestions) |
| **Visualization**         | Pandas, Matplotlib (skill-gap heatmaps, ranking insights)                  |
| **File Parsing**          | PyPDF2 / python-docx                                                       |

**🧪 System Workflow:**

1️⃣ Resume Upload

User uploads PDF/DOCX → Stored in S3 → Lambda is triggered.

2️⃣ Lambda Processing

Lambda fetches real-time job listings → normalizes job records → deduplicates → stores jobs in MongoDB.

3️⃣ Streamlit Ranking

Streamlit:

Computes embeddings

Scores each job

Creates Top-20 job recommendations

4️⃣ LLM Skill-Gap & Reasoning

Optional: GPT-4o / GPT-5.1

Missing skills

Explanation

Personalized advice

5️⃣ Visualization

Skill-gap heatmap

Recommended Coursera courses

Design Choice:
Matching is performed at request time to ensure resume-specific personalization and reduce backend compute costs.

🏁 Conclusion

This project successfully implements a full end-to-end AI-driven Job Recommendation System that mimics real industry-grade platforms.
It integrates NLP, vector embeddings, LLM reasoning, cloud automation, and real-time UI visualization into one seamless pipeline.



