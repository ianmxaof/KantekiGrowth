import spacy
from typing import List, Dict

nlp = spacy.load("en_core_web_sm")

EFFORT_SIGNALS = ["automation", "internal tools", "maintenance", "support"]


def analyze_job_description(text: str) -> Dict:
    doc = nlp(text)
    skills = []
    responsibilities = []
    for sent in doc.sents:
        if any(signal in sent.text.lower() for signal in EFFORT_SIGNALS):
            responsibilities.append(sent.text)
        # Naive skill extraction: look for nouns that are likely skills
        for token in sent:
            if token.pos_ == "NOUN" and token.text.istitle():
                skills.append(token.text)
    return {
        "skills": list(set(skills)),
        "responsibilities": responsibilities,
        "effort_score": len(responsibilities),
    }

if __name__ == "__main__":
    sample = """We are looking for a Python developer to automate internal tools and support backend systems. Experience with maintenance and scripting is a plus."""
    print(analyze_job_description(sample)) 