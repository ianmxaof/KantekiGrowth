from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from resume_builder import generate_resume_for_job, render_resume
import os

app = FastAPI()

# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeJobRequest(BaseModel):
    job_description: str = None
    job_url: str = None
    profile: dict = None
    use_llm: bool = False

def extract_job_description_with_llm(html: str) -> str:
    import os
    import requests
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise Exception('OPENAI_API_KEY not set')
    prompt = (
        "Extract only the main job description, responsibilities, and requirements from the following HTML or text. "
        "Return only the relevant job description content, no extra commentary.\n\n" + html[:12000]
    )
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts job descriptions from HTML."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.2,
    }
    resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result['choices'][0]['message']['content'].strip()

def extract_job_description_from_html(html: str, use_llm: bool = False) -> str:
    if use_llm:
        try:
            return extract_job_description_with_llm(html)
        except Exception as e:
            print(f"LLM extraction failed: {e}. Falling back to heuristics.")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    # Heuristic: prioritize sections with key phrases
    KEYWORDS = [
        'responsibilities', 'requirements', 'qualifications', 'about the job',
        'what you will do', 'what you need', 'skills', 'who you are', 'job description',
    ]
    text_blocks = []
    for tag in soup.find_all(['section', 'div', 'article']):
        block_text = tag.get_text(separator=' ', strip=True).lower()
        if any(kw in block_text for kw in KEYWORDS):
            text_blocks.append(tag.get_text(separator=' ', strip=True))
    # If found, join and return
    if text_blocks:
        return '\n\n'.join(text_blocks)
    # Fallback: join all <p> tags
    paragraphs = [p.get_text() for p in soup.find_all('p')]
    if paragraphs:
        return '\n'.join(paragraphs)
    # Fallback: all text
    return soup.get_text()

@app.post("/analyze-job")
async def analyze_job(req: AnalyzeJobRequest):
    job_desc = req.job_description
    use_llm = req.use_llm or bool(os.environ.get('USE_LLM'))
    # If job_url is provided, fetch and extract job description
    if req.job_url:
        try:
            import requests
            resp = requests.get(req.job_url, timeout=10)
            job_desc = extract_job_description_from_html(resp.text, use_llm=use_llm)
        except Exception as e:
            return {"error": f"Failed to fetch or parse job URL: {e}"}
    if not job_desc:
        return {"error": "No job description or URL provided."}
    # Generate resume and checklist (in-memory, not writing files)
    from job_analyzer import analyze_job_description
    from resume_builder import load_experiences, sort_and_group_experiences
    analysis = analyze_job_description(job_desc)
    required_skills = analysis['skills']
    # Use profile if provided, else default
    profile = req.profile or {}
    name = profile.get('name', 'Ian Murphy')
    contact = profile.get('contact', 'ianelliotmurphy2012@gmail.com | 408-786-4871 | San Jose, CA')
    # If user provided experiences, use them, else load from YAMLs
    if profile.get('experiences'):
        main_experiences = profile['experiences']
    else:
        experiences = load_experiences()
        main_experiences = sort_and_group_experiences(experiences, required_skills)
    context = {
        'name': name,
        'contact': contact,
        'summary': f"Senior engineer with expertise in {', '.join(required_skills[:3])}. {analysis['responsibilities'][0] if analysis['responsibilities'] else ''}",
        'skills': required_skills,
        'main_experiences': main_experiences,
    }
    resume_md = render_resume(context, output_filename="resume_api.md")
    # Checklist
    analysis = analyze_job_description(job_desc)
    required_skills = analysis.get('skills', [])
    responsibilities = analysis.get('responsibilities', [])
    checklist = [
        '# Interview Prep Checklist',
        '',
        '## Core Technical Topics',
    ]
    for skill in required_skills:
        checklist.append(f'- Master: **{skill}**')
    checklist.append('')
    checklist.append('## Responsibilities & Scenarios')
    for resp in responsibilities:
        checklist.append(f'- Prepare to discuss: {resp}')
    checklist.append('')
    checklist.append('## Resume Alignment')
    checklist.append('- Be ready to explain and give examples for every skill and project listed on your resume.')
    checklist.append('- Prepare STAR (Situation, Task, Action, Result) stories for leadership, problem-solving, and AI tool development.')
    checklist.append('')
    checklist.append('## AI & LLMs')
    checklist.append('- Review latest developments in generative AI and LLMs (OpenAI, Claude, etc.).')
    checklist.append('- Understand agentic workflows and how AI can automate developer tasks.')
    checklist.append('')
    checklist.append('## Frontend & Developer Tools')
    checklist.append('- Brush up on React, TypeScript, and modern frontend tooling.')
    checklist.append('- Be ready to discuss developer workflow pain points and how to solve them with AI.')
    checklist.append('')
    checklist.append('## Communication & Collaboration')
    checklist.append('- Practice explaining technical concepts to non-experts.')
    checklist.append('- Prepare examples of cross-team collaboration and mentoring.')
    checklist.append('')
    checklist.append('---')
    checklist.append('**Pro Tip:** Research Adobe\'s latest AI initiatives and be ready to discuss how you can contribute.')
    checklist_md = '\n'.join(checklist)
    return {
        "resume_md": resume_md,
        "checklist_md": checklist_md,
        "extracted_job_description": job_desc
    } 