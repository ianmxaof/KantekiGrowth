import os
import sys
from resume_builder import main as build_resume

def batch_generate(job_dir, output_dir):
    for fname in os.listdir(job_dir):
        if fname.endswith('.txt'):
            job_path = os.path.join(job_dir, fname)
            # Optionally, parse job description and pass to resume builder
            # For now, just print the job being processed
            print(f"Generating resume for: {fname}")
            # TODO: Integrate job description parsing and tailored resume generation
            build_resume()
            # Move or rename output as needed

if __name__ == "__main__":
    job_dir = sys.argv[1] if len(sys.argv) > 1 else 'jobs/'
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output/'
    batch_generate(job_dir, output_dir) 