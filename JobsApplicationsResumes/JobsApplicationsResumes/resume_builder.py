import os
import yaml
import glob
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from job_analyzer import analyze_job_description

EXPERIENCE_DIR = os.path.join(os.path.dirname(__file__), 'experiences')
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

# Helper to parse dates
def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m')

def load_experiences():
    files = glob.glob(os.path.join(EXPERIENCE_DIR, '*.yaml'))
    exps = []
    for f in files:
        with open(f, 'r') as fp:
            exps.append(yaml.safe_load(fp))
    return exps

def sort_and_group_experiences(experiences):
    # Sort by start date descending
    experiences.sort(key=lambda x: parse_date(x['start']), reverse=True)
    main_exps = []
    side_exps = []
    for exp in experiences:
        if exp.get('type', 'main') == 'main':
            main_exps.append(exp)
        else:
            side_exps.append(exp)
    # Assign side projects to main jobs if overlapping
    for main in main_exps:
        main_start = parse_date(main['start'])
        main_end = parse_date(main['end'])
        main['side_projects'] = []
        for side in side_exps:
            side_start = parse_date(side['start'])
            side_end = parse_date(side['end'])
            if (side_start <= main_end and side_end >= main_start):
                main['side_projects'].append(side)
    return main_exps

def render_resume(context):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template('main_resume.md.j2')
    return template.render(**context)

def generate_interview_checklist(job_desc, resume_content, output_filename):
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
    checklist.append("**Pro Tip:** Research Adobe's latest AI initiatives and be ready to discuss how you can contribute.")
    with open(os.path.join(OUTPUT_DIR, output_filename), 'w') as f:
        f.write('\n'.join(checklist))
    print(f'Interview checklist generated at output/{output_filename}')

def generate_resume_for_job(job_desc, output_filename=None):
    analysis = analyze_job_description(job_desc)
    required_skills = analysis['skills']
    context = {
        'name': 'Ian Murphy',
        'contact': 'ianelliotmurphy2012@gmail.com | 408-786-4871 | San Jose, CA',
        'summary': f"Senior engineer with expertise in {', '.join(required_skills[:3])}. {analysis['responsibilities'][0] if analysis['responsibilities'] else ''}",
        'skills': required_skills,
    }
    experiences = load_experiences()
    context['main_experiences'] = sort_and_group_experiences(experiences, required_skills)
    if not output_filename:
        output_filename = 'resume_' + '_'.join(required_skills[:2]).replace(' ', '_') + '.md'
    resume_content = render_resume(context, output_filename)
    # Generate interview checklist
    checklist_filename = 'interview_checklist_' + '_'.join(required_skills[:2]).replace(' ', '_') + '.md'
    generate_interview_checklist(job_desc, resume_content, checklist_filename)

def main():
    import sys
    if len(sys.argv) > 1:
        job_desc_file = sys.argv[1]
        with open(job_desc_file, 'r') as f:
            job_desc = f.read()
        generate_resume_for_job(job_desc)
    else:
        context = {
            'name': 'Ian Murphy',
            'contact': 'ianelliotmurphy2012@gmail.com | 408-786-4871 | San Jose, CA',
            'summary': 'Overqualified automation engineer with deep experience in async, distributed systems, and agent orchestration. Seeking to bring advanced skills to entry-level roles.',
            'skills': ['Python', 'AsyncIO', 'Distributed Systems', 'CI/CD', 'Agent Mesh', 'Automation'],
        }
        experiences = load_experiences()
        context['main_experiences'] = sort_and_group_experiences(experiences)
        output = render_resume(context)
        with open(os.path.join(OUTPUT_DIR, 'resume_silicon_valley.md'), 'w') as f:
            f.write(output)
        print('Resume generated at output/resume_silicon_valley.md')

if __name__ == '__main__':
    main() 