import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
]

def random_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def apply_to_job(job_link, resume_path, applicant_info):
    options = Options()
    options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
    driver = webdriver.Chrome(options=options)
    driver.get(job_link)
    random_delay(2, 5)
    # Example: fill out a generic application form
    try:
        # Find and fill name/email fields (customize selectors as needed)
        name_field = driver.find_element(By.CSS_SELECTOR, 'input[name*="name" i]')
        email_field = driver.find_element(By.CSS_SELECTOR, 'input[type="email"]')
        human_type(name_field, applicant_info['name'])
        random_delay()
        human_type(email_field, applicant_info['email'])
        random_delay()
        # Upload resume (customize selector as needed)
        upload_field = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        upload_field.send_keys(resume_path)
        random_delay()
        # Submit (customize selector as needed)
        submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
        submit_btn.click()
        random_delay(2, 4)
        print(f"Applied to {job_link}")
    except Exception as e:
        print(f"Failed to apply to {job_link}: {e}")
    driver.quit()

if __name__ == "__main__":
    # Example usage
    job_link = 'https://www.example.com/job/apply/12345'
    resume_path = 'output/resume_python_developer.md'
    applicant_info = {
        'name': 'Your Name',
        'email': 'your.email@example.com',
    }
    apply_to_job(job_link, resume_path, applicant_info) 