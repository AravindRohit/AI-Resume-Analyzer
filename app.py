import streamlit as st
import os
import time
import hashlib
from dotenv import load_dotenv

load_dotenv()

from pdf_parser import extract_text_from_pdf, PDFParseError
from embeddings import compute_match_score
from llm_analyzer import analyze_resume_with_llm
from report_generator import generate_pdf_report
from validators import (validate_resume_text, validate_job_description, ValidationError,)
from utils import sanitize_text, truncate_text

# -- Page config ---------------------------------------------------------------
st.set_page_config(page_title="SmartResume AI", layout="wide", initial_sidebar_state="expanded",)

# -- Custom CSS ----------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .score-card {
        background: linear-gradient(135deg, #0f3460, #533483);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        color: white;
        margin: 1rem 0;
    }
    .score-number {
        font-size: 3.5rem;
        font-weight: bold;
        color: #e94560;
    }
    .section-card {
        background: #f8f9fa;
        border-left: 4px solid #0f3460;
        border-radius: 8px;
        padding: 1.2rem;
        margin: 0.8rem 0;
    }
    .strength-item { color: #28a745; font-weight: 500; }
    .improvement-item { color: #dc3545; font-weight: 500; }
    .missing-item { color: #fd7e14; font-weight: 500; }
    .stProgress > div > div { background-color: #0f3460; }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #dc3545;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .metric-pill {
        display: inline-block;
        background: #e9ecef;
        border-radius: 20px;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        font-size: 0.85rem;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -- Header --------------------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
        <h1>SmartResume AI</h1>
        <p style="font-size:1.1rem; opacity:0.85;">
            AI-Powered Resume Analyzer and Job Matcher
        </p>
        <p style="font-size:0.85rem; opacity:0.6;">
            Intelligent multi-agent analysis · Semantic matching · Professional report generation
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -- Sidebar -------------------------------------------------------------------
with st.sidebar:
    st.header("Configuration")

    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        os.environ["GROQ_API_KEY"] = env_key
    else:
        st.warning("GROQ_API_KEY not found in environment. Please set it in your .env file.")

    st.divider()
    st.markdown("**How it works**")
    st.markdown(
        "1. **Document extraction** — reads and cleans your PDF\n"
        "2. **Semantic comparison** — measures meaning-level alignment\n"
        "3. **Agent analysis** — two specialised AI agents review your profile\n"
        "4. **Report generation** — produces a downloadable PDF summary"
    )
    st.divider()
    st.markdown("**Pipeline**")
    st.markdown(
        "Profile extraction\n"
        "Gap and fit analysis\n"
        "Scored PDF report"
    )

# -- Session state -------------------------------------------------------------
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "last_input_hash" not in st.session_state:
    st.session_state.last_input_hash = None
if "report_bytes" not in st.session_state:
    st.session_state.report_bytes = None


def compute_input_hash(resume_text: str, jd_text: str) -> str:
    """Prevent duplicate analysis on identical inputs."""
    combined = (resume_text.strip() + jd_text.strip()).encode("utf-8")
    return hashlib.md5(combined).hexdigest()


# -- Input columns -------------------------------------------------------------
col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.subheader("Upload Resume (PDF)")
    uploaded_resume = st.file_uploader("Choose a PDF file", type=["pdf"], key="resume_uploader", help="Supports text-based PDFs up to ~50 MB, 1-60 pages.",)
    resume_text = ""
    if uploaded_resume:
        with st.spinner("Extracting resume content..."):
            try:
                resume_bytes = uploaded_resume.read()
                resume_text = extract_text_from_pdf(resume_bytes, source="Resume")
                validate_resume_text(resume_text)
                word_count = len(resume_text.split())
                st.success(f"Resume ready — {word_count} words ({uploaded_resume.name})")
                with st.expander("Preview extracted text"):
                    st.text(truncate_text(resume_text, max_chars=1500))
            except PDFParseError as e:
                st.markdown(f'<div class="error-box"><b>Document error:</b> {e}</div>', unsafe_allow_html=True,)
                resume_text = ""
            except ValidationError as e:
                st.markdown(f'<div class="warning-box"><b>Validation notice:</b> {e}</div>', unsafe_allow_html=True,)
                resume_text = ""

with col_right:
    st.subheader("Job Description")
    jd_input_mode = st.radio(
        "Input method", ["Paste text", "Upload PDF"], horizontal=True, key="jd_mode"
    )
    jd_text = ""
    if jd_input_mode == "Paste text":
        jd_raw = st.text_area("Paste job description here", height=200, placeholder="e.g. We are looking for a Python developer with experience in...",)
        jd_text = sanitize_text(jd_raw)
    else:
        uploaded_jd = st.file_uploader("Upload job description as PDF", type=["pdf"], key="jd_uploader")
        if uploaded_jd:
            try:
                jd_bytes = uploaded_jd.read()
                jd_text = extract_text_from_pdf(jd_bytes, source="Job Description")
                st.success(f"Job description ready — {len(jd_text.split())} words")
            except PDFParseError as e:
                st.markdown(f'<div class="error-box">{e}</div>', unsafe_allow_html=True)

    if jd_text:
        try:
            validate_job_description(jd_text)
            st.success(f"Job description ready — {len(jd_text.split())} words")
        except ValidationError as e:
            st.markdown(f'<div class="warning-box">{e}</div>', unsafe_allow_html=True)
            jd_text = ""

# -- Analyse button ------------------------------------------------------------
st.divider()

can_analyse = bool(resume_text and jd_text and os.environ.get("GROQ_API_KEY"))

if not os.environ.get("GROQ_API_KEY"):
    st.info("Add GROQ_API_KEY to your .env file to enable analysis.")

analyse_btn = st.button("Analyse Resume", disabled=not can_analyse, use_container_width=True, type="primary",)

if analyse_btn and can_analyse:
    current_hash = compute_input_hash(resume_text, jd_text)

    if current_hash == st.session_state.last_input_hash:
        st.warning("These exact inputs were already analysed — scroll down to see your results.")
    else:
        progress_bar = st.progress(0, text="Starting analysis...")

        try:
            progress_bar.progress(20, text="Computing semantic alignment...")
            match_score, skill_overlap = compute_match_score(resume_text, jd_text)

            progress_bar.progress(50, text="Running agent pipeline...")
            llm_result = analyze_resume_with_llm(resume_text, jd_text, match_score)

            progress_bar.progress(85, text="Building PDF report...")
            report_bytes = generate_pdf_report(resume_text=resume_text, jd_text=jd_text, match_score=match_score, skill_overlap=skill_overlap, llm_result=llm_result,)

            progress_bar.progress(100, text="Done!")
            time.sleep(0.4)
            progress_bar.empty()

            st.session_state.analysis_result = {
                "match_score": match_score,
                "skill_overlap": skill_overlap,
                "llm_result": llm_result,
            }
            st.session_state.last_input_hash = current_hash
            st.session_state.report_bytes = report_bytes

        except Exception as exc:
            progress_bar.empty()
            st.markdown(f'<div class="error-box"><b>Analysis failed:</b> {exc}<br>'"Please check and try again.</div>", unsafe_allow_html=True,)

# -- Results -------------------------------------------------------------------
result = st.session_state.analysis_result
if result:
    st.divider()
    st.header("Analysis Results")

    match_score = result["match_score"]
    skill_overlap = result["skill_overlap"]
    llm = result["llm_result"]

    if match_score >= 75:
        score_label = "Strong Match"
    elif match_score >= 50:
        score_label = "Moderate Match"
    else:
        score_label = "Weak Match"

    # Score card
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            f"""
            <div class="score-card">
                <div style="font-size:1rem; opacity:0.8;">Overall Match Score</div>
                <div class="score-number">{match_score:.1f}%</div>
                <div style="font-size:1.1rem;">{score_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(int(match_score) / 100)

    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Alignment Score", f"{match_score:.1f}%")
    m2.metric("Skill Coverage", f"{skill_overlap:.1f}%")
    m3.metric("Gaps Identified", len(llm.get("missing_skills", [])), delta_color="inverse")
    m4.metric("Matching Points", len(llm.get("strengths", [])))

    st.divider()

    col_s, col_i = st.columns(2, gap="large")

    with col_s:
        st.subheader("What Works Well")
        strengths = llm.get("strengths", [])
        if strengths:
            for s in strengths:
                st.markdown(f'<div class="section-card strength-item">{s}</div>', unsafe_allow_html=True)
        else:
            st.info("No strong matches detected for this role.")

    with col_i:
        st.subheader("Suggested Improvements")
        improvements = llm.get("improvements", [])
        if improvements:
            for imp in improvements:
                st.markdown(f'<div class="section-card improvement-item">{imp}</div>', unsafe_allow_html=True)
        else:
            st.success("No major improvements needed.")

    st.divider()

    st.subheader("Missing Skills")
    missing = llm.get("missing_skills", [])
    if missing:
        pills_html = "".join(
            f'<span class="metric-pill missing-item">{sk}</span>' for sk in missing
        )
        st.markdown(pills_html, unsafe_allow_html=True)
    else:
        st.success("No critical skill gaps detected!")

    st.divider()

    if llm.get("summary"):
        st.subheader("Overall Assessment")
        st.markdown(f'<div class="section-card">{llm["summary"]}</div>', unsafe_allow_html=True,)

    if llm.get("ats_keywords"):
        st.subheader("Keywords to Strengthen Your Application")
        kw_html = "".join(
            f'<span class="metric-pill">{kw}</span>'
            for kw in llm["ats_keywords"]
        )
        st.markdown(kw_html, unsafe_allow_html=True)

    st.divider()

    if st.session_state.report_bytes:
        st.subheader("Download Your Report")
        st.download_button(label="Download Full PDF Report", data=st.session_state.report_bytes, file_name="SmartResume_AI_Report.pdf", mime="application/pdf", use_container_width=True, type="primary",)
        st.caption("Includes: match score, strengths, skill gaps, improvements, and recommended keywords.")
