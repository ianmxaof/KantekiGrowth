import json

# File paths
raw_prompt_file = "cleaned_prompt_list.txt"
repo_file = "prompt_repo.json"

def load_prompts():
    # Open and read the cleaned prompt list
    with open(raw_prompt_file, 'r') as f:
        return f.read().strip().split("\n")  # Each prompt is a new line in the file

def load_existing_repo():
    # Try to load existing repo, if it doesn't exist, return an empty list
    try:
        with open(repo_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_to_repo(prompts):
    # Load existing repo and append new prompts
    repo = load_existing_repo()
    for prompt in prompts:
        prompt_entry = {
            "prompt": prompt,
            "id": len(repo) + 1  # Simple ID increment
        }
        repo.append(prompt_entry)

    # Save the updated repo back to the file
    with open(repo_file, 'w') as f:
        json.dump(repo, f, indent=4)

def main():
    # Get cleaned prompts and load existing repository
    cleaned_prompts = load_prompts()
    save_to_repo(cleaned_prompts)
    print(f"Successfully added {len(cleaned_prompts)} new prompts.")

if __name__ == "__main__":
    main()
