from __future__ import annotations
import json
import os
import re
from typing import Any
from crewai import Agent, Crew, LLM, Task
from dotenv import load_dotenv

load_dotenv()


# ── LLM factory ──────────────────────────────────────────────────────────────

def _build_llm() -> LLM:
    """
    Construct the Groq LLM instance.
    Raises ValueError with a helpful message if the key is missing.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("LLM Error - Missing Some Important Information\n")
    return LLM(model="groq/llama-3.3-70b-versatile", api_key=api_key, temperature=0,)


# ── Agent definitions ─────────────────────────────────────────────────────────
def _resume_parser_agent(llm: LLM) -> Agent:
    return Agent(
        role="Resume Information Extractor",
        goal=(
            "Extract all relevant professional details from a candidate's resume: "
            "technical skills, tools, programming languages, years of experience, "
            "educational background, project highlights, and certifications."
        ),
        backstory=(
            "You are a meticulous HR data analyst with 10 years of experience "
            "parsing resumes across tech industries. You focus purely on what is "
            "explicitly stated in the document — you never infer or hallucinate."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _match_analyst_agent(llm: LLM) -> Agent:
    return Agent(
        role="Job Fit Analyst and Career Coach",
        goal=(
            "Compare a candidate's extracted resume profile against a job description "
            "and produce a structured JSON evaluation covering match score context, "
            "strengths, missing skills, actionable improvements, and ATS keywords."
        ),
        backstory=(
            "You are a senior technical recruiter and career coach who has evaluated "
            "thousands of candidates. You give honest, constructive, and specific "
            "feedback. You always respond with valid JSON and nothing else."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


# ── Task definitions ──────────────────────────────────────────────────────────

def _parse_task(agent: Agent, resume_text: str) -> Task:
    return Task(
        description=(
            f"Extract a structured profile from the following resume.\n\n"
            f"=== RESUME ===\n{resume_text[:3500]}\n\n"
            "List: technical skills, tools, programming languages, "
            "years of experience, education, and notable projects. "
            "Be factual — only include what is explicitly mentioned."
        ),
        expected_output=(
            "A concise bullet-point profile of the candidate covering: "
            "skills, tools, experience level, education, and key projects."
        ),
        agent=agent,
    )


def _analysis_task(agent: Agent, jd_text: str, match_score: float) -> Task:
    schema = """{
  "summary": "<2-3 sentence professional summary of the candidate's fit>",
  "strengths": ["<strength 1>", ...],
  "missing_skills": ["<missing skill 1>", ...],
  "improvements": ["<actionable suggestion 1>", ...],
  "ats_keywords": ["<keyword 1>", ...],
  "experience_match": "<Strong|Moderate|Weak>",
  "education_match": "<Strong|Moderate|Weak|Not Specified>",
  "hiring_recommendation": "<Recommended|Maybe|Not Recommended>"
}"""
    return Task(
        description=(
            f"Using the candidate profile from the previous task, evaluate fit against "
            f"the job description below. The pre-computed semantic match score is "
            f"{match_score:.1f}% — use this as context.\n\n"
            f"=== JOB DESCRIPTION ===\n{jd_text[:2500]}\n\n"
            f"Respond with ONLY valid JSON matching this exact schema:\n{schema}\n\n"
            "Rules:\n"
            "- strengths: max 8 items — concrete skills/experiences that match the JD\n"
            "- missing_skills: max 10 items — critical JD skills absent from the resume\n"
            "- improvements: max 8 items — specific, actionable resume edits\n"
            "- ats_keywords: max 12 items — exact JD keywords to add for ATS systems\n"
            "- Do NOT hallucinate skills absent from the resume profile."
        ),
        expected_output=(
            "A single valid JSON object matching the schema above. "
            "No markdown fences, no explanation outside the JSON."
        ),
        agent=agent,
        context=[],  # populated dynamically below
    )


# ── JSON parsing helper ───────────────────────────────────────────────────────
def _safe_parse_json(raw: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON; fall back gracefully."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {
        "summary": "Analysis parsing error — could not decode the model response.",
        "strengths": [],
        "missing_skills": [],
        "improvements": ["Please retry the analysis."],
        "ats_keywords": [],
        "experience_match": "Not Specified",
        "education_match": "Not Specified",
        "hiring_recommendation": "Not Specified",
    }


def _normalise(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure all expected keys exist with correct types."""
    defaults: dict[str, Any] = {
        "summary": "",
        "strengths": [],
        "missing_skills": [],
        "improvements": [],
        "ats_keywords": [],
        "experience_match": "Not Specified",
        "education_match": "Not Specified",
        "hiring_recommendation": "Not Specified",
    }
    for key, default in defaults.items():
        if key not in data:
            data[key] = default
        elif isinstance(default, list) and not isinstance(data[key], list):
            data[key] = [str(data[key])] if data[key] else []
        elif isinstance(default, str) and not isinstance(data[key], str):
            data[key] = str(data[key])
    return data


# ── Public API ────────────────────────────────────────────────────────────────
def analyze_resume_with_llm(resume_text: str, jd_text: str, match_score: float,) -> dict[str, Any]:

    llm = _build_llm()

    parser_agent = _resume_parser_agent(llm)
    analyst_agent = _match_analyst_agent(llm)

    parse_t = _parse_task(parser_agent, resume_text)
    analyse_t = _analysis_task(analyst_agent, jd_text, match_score)
    analyse_t.context = [parse_t] 

    crew = Crew(agents=[parser_agent, analyst_agent], tasks=[parse_t, analyse_t], verbose=False,)

    try:
        result = crew.kickoff()
        raw_output: str = result.raw if hasattr(result, "raw") else str(result)
    except Exception as exc:
        raise RuntimeError(f"CrewAI pipeline failed: {exc}") from exc

    parsed = _safe_parse_json(raw_output)
    return _normalise(parsed)
