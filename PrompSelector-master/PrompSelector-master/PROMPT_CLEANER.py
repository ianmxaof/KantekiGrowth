import os
import json
import re
from plyer import notification  # install with: pip install plyer

RAW_FILE = 'raw_prompts.txt'
REPO_FILE = 'prompt_repo.json'

def clean_prompt_text(text):
    # Remove timestamps, usernames, URLs, emojis, and unwanted characters
    text = re.sub(r'\d{1,2}:\d{2}(am|pm)?', '', text, flags=re.IGNORECASE)  # timestamps
    text = re.sub(r'@\w+|#\w+', '', text)  # usernames or hashtags
    text = re.sub(r'http\S+', '', text)  # links
    text = re.sub(r'[^\w\s.,?!\'":;\-()]+', '', text)  # weird symbols/emojis
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_existing_prompts():
    if not os.path.exists(REPO_FILE):
        return []
    with open(REPO_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_prompts(prompts):
    with open(REPO_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

def clean_and_update():
    if not os.path.exists(RAW_FILE):
        return 0

    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    cleaned_prompts = [clean_prompt_text(line) for line in raw_lines if line.strip()]
    cleaned_prompts = list(set(cleaned_prompts))  # remove duplicates

    existing_prompts = load_existing_prompts()
    new_prompts = [p for p in cleaned_prompts if p not in existing_prompts]

    if new_prompts:
        updated = existing_prompts + new_prompts
        save_prompts(updated)

    # Clear the raw file so we don’t double-process
    open(RAW_FILE, 'w', encoding='utf-8').close()

    return len(new_prompts)

if __name__ == "__main__":
    count = clean_and_update()
    if count:
        print(f"✅ {count} new prompts cleaned and added.")
        notification.notify(
            title="Prompt Cleaner",
            message=f"{count} new prompt(s) added to prompt_repo.json",
            timeout=3
        )
    else:
        print("⚠️ No new prompts found.")
