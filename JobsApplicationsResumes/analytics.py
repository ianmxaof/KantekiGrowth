import csv
from datetime import datetime

def log_application(job_title, company, resume_version, status):
    with open('application_log.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            datetime.now().isoformat(),
            job_title,
            company,
            resume_version,
            status
        ])

def get_stats():
    stats = {}
    with open('application_log.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            status = row[4]
            stats[status] = stats.get(status, 0) + 1
    return stats

if __name__ == "__main__":
    log_application('Python Developer', 'Acme Corp', 'v1', 'applied')
    print(get_stats()) 