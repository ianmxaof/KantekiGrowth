import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

SCRAPER_CONFIG = {
    "keywords": [
        "python", "developer", "software", "engineer", "automation", "backend", "scripting", "AI", "tools"
    ],
    "salary_min": 70000,
    "salary_target": 100000,
    "work_types": ["remote", "hybrid", "on-site"],
    "exclude_keywords": ["open source", "proof of work", "hackathon", "community"],
    "effort_signals": ["automation", "internal tools", "maintenance", "support"],
}

def search_linkedin_jobs():
    driver = webdriver.Chrome()
    driver.get('https://www.linkedin.com/jobs/')
    time.sleep(3)
    search_box = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Search jobs"]')
    search_box.send_keys(' '.join(SCRAPER_CONFIG["keywords"]))
    search_box.send_keys(Keys.RETURN)
    time.sleep(3)
    # TODO: Add salary, work type, and effort signal filtering
    jobs = []
    # Example: scrape first 10 jobs
    job_cards = driver.find_elements(By.CSS_SELECTOR, '.jobs-search-results__list-item')[:10]
    for card in job_cards:
        try:
            title = card.find_element(By.CSS_SELECTOR, 'h3').text
            company = card.find_element(By.CSS_SELECTOR, '.base-search-card__subtitle').text
            location = card.find_element(By.CSS_SELECTOR, '.job-search-card__location').text
            link = card.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
            jobs.append({"title": title, "company": company, "location": location, "link": link})
        except Exception as e:
            continue
    driver.quit()
    return jobs

if __name__ == "__main__":
    jobs = search_linkedin_jobs()
    for job in jobs:
        print(job) 