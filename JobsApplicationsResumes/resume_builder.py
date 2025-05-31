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

def sort_and_group_experiences(experiences, required_skills=None):
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
    # Optionally filter or boost experiences by required_skills
    if required_skills:
        def score_exp(exp):
            return len(set(exp.get('skills', [])) & set(required_skills))
        main_exps.sort(key=score_exp, reverse=True)
    return main_exps

def render_resume(context, output_filename):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template('main_resume.md.j2')
    output = template.render(**context)
    with open(os.path.join(OUTPUT_DIR, output_filename), 'w') as f:
        f.write(output)
    print(f'Resume generated at output/{output_filename}')

def generate_resume_for_job(job_desc, output_filename=None):
    analysis = analyze_job_description(job_desc)
    required_skills = analysis['skills']
    # User info (customize or load from config)
    context = {
        'name': 'Your Name',
        'contact': 'your.email@example.com | (555) 555-5555 | San Jose, CA',
        'summary': f"Senior engineer with expertise in {', '.join(required_skills[:3])}. {analysis['responsibilities'][0] if analysis['responsibilities'] else ''}",
        'skills': required_skills,
    }
    experiences = load_experiences()
    context['main_experiences'] = sort_and_group_experiences(experiences, required_skills)
    if not output_filename:
        output_filename = 'resume_' + '_'.join(required_skills[:2]).replace(' ', '_') + '.md'
    render_resume(context, output_filename)

def main():
    import sys
    if len(sys.argv) > 1:
        job_desc_file = sys.argv[1]
        with open(job_desc_file, 'r') as f:
            job_desc = f.read()
        generate_resume_for_job(job_desc)
    else:
        # Default: generate generic resume
        context = {
            'name': 'Your Name',
            'contact': 'your.email@example.com | (555) 555-5555 | San Jose, CA',
            'summary': 'Overqualified automation engineer with deep experience in async, distributed systems, and agent orchestration. Seeking to bring advanced skills to entry-level roles.',
            'skills': ['Python', 'AsyncIO', 'Distributed Systems', 'CI/CD', 'Agent Mesh', 'Automation'],
        }
        experiences = load_experiences()
        context['main_experiences'] = sort_and_group_experiences(experiences)
        render_resume(context, 'resume_silicon_valley.md')

if __name__ == '__main__':
    main() 