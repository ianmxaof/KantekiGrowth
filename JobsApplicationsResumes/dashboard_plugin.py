from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
import os
import shutil
import analytics
import apply_bot

app = FastAPI()

@app.post('/upload-job-desc')
def upload_job_desc(file: UploadFile = File(...)):
    job_dir = 'jobs/'
    os.makedirs(job_dir, exist_ok=True)
    file_path = os.path.join(job_dir, file.filename)
    with open(file_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename}

@app.post('/generate-resume')
def generate_resume(job_filename: str):
    # TODO: Integrate with resume_batcher or resume_builder
    return {"status": "Resume generation triggered for " + job_filename}

@app.get('/resumes')
def list_resumes():
    resumes = [f for f in os.listdir('output/') if f.endswith('.md') or f.endswith('.pdf')]
    return {"resumes": resumes}

@app.get('/download-resume/{filename}')
def download_resume(filename: str):
    file_path = os.path.join('output/', filename)
    return FileResponse(file_path)

@app.post('/log-callback')
def log_callback(job_title: str, company: str, resume_version: str, status: str):
    analytics.log_application(job_title, company, resume_version, status)
    return {"status": "Logged"}

@app.get('/analytics')
def get_analytics():
    return JSONResponse(content=analytics.get_stats())

@app.post('/apply-job')
def apply_job(job_link: str, resume_path: str, name: str, email: str):
    applicant_info = {'name': name, 'email': email}
    apply_bot.apply_to_job(job_link, resume_path, applicant_info)
    return {"status": f"Applied to {job_link}"}

@app.get('/application-log')
def application_log():
    log_path = 'application_log.csv'
    if not os.path.exists(log_path):
        return JSONResponse(content={"log": []})
    with open(log_path, 'r') as f:
        lines = f.readlines()
    return JSONResponse(content={"log": lines}) 