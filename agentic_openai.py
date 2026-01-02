# utils/agentic_openai.py
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# SIMPLE RATE LIMITER
# --------------------------------------------------
class OpenAIRateLimiter:
    def __init__(self, max_calls_per_minute=15):
        self.max_calls = max_calls_per_minute
        self.calls = []

    def wait(self):
        now = time.time()
        self.calls = [t for t in self.calls if now - t < 60]

        if len(self.calls) >= self.max_calls:
            sleep_time = 60 - (now - self.calls[0]) + 1
            logger.info(f"Rate limit reached. Waiting {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self.calls = []

        self.calls.append(time.time())


rate_limiter = OpenAIRateLimiter()


# --------------------------------------------------
# AI-BASED JOB MATCH EXPLANATION (NO SKILL INFERENCE)
# --------------------------------------------------
def generate_ai_explanation(
    api_key: str,
    job_title: str,
    job_description: str,
    resume_skills: list,
    job_skills: list,
    missing_skills: list,
    model: str = "gpt-4o-mini"
) -> str:
    """
    Generate an AI-based explanation using PRE-COMPUTED skills.
    AI must not infer or invent skills.
    """

    if not api_key or not api_key.startswith("sk-"):
        return "AI explanation unavailable (API key missing or invalid)."

    system_prompt = (
        "You are an AI career advisor. "
        "Explain job fit clearly and professionally. "
        "You MUST use only the provided skill lists. "
        "Do NOT invent or assume additional skills."
    )

    user_prompt = f"""
Job Title:
{job_title}

Job Description (summary):
{job_description[:800]}

Candidate Skills:
{', '.join(resume_skills) if resume_skills else 'None'}

Job Required Skills:
{', '.join(job_skills) if job_skills else 'None'}

Missing Skills:
{', '.join(missing_skills) if missing_skills else 'None'}

Task:
Write a concise explanation (3–4 sentences) covering:
1. Overall match quality
2. Key strengths
3. Skill gaps and improvement areas
"""

    rate_limiter.wait()

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "input": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "temperature": 0.3,
                "max_output_tokens": 220
            },
            timeout=20
        )

        if response.status_code != 200:
            logger.warning(f"OpenAI error {response.status_code}: {response.text}")
            return "AI explanation could not be generated (OpenAI error)."

        data = response.json()
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        return c.get("text", "").strip()

        return "AI explanation unavailable (empty response)."

    except Exception as e:
        logger.error(f"AI explanation failed: {e}")
        return "AI explanation could not be generated due to a system issue."