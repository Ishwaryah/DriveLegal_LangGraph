import json
import os

RULES_PATH = r"c:\Users\USER\Downloads\DriveLegal-main\DriveLegal-main\backend\data\rules.json"

def clean_rules():
    if not os.path.exists(RULES_PATH):
        print(f"File not found: {RULES_PATH}")
        return

    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cleaned_count = 0
    for rule in data.get('rules', []):
        title = rule.get('title', '')
        description = rule.get('description', '')

        new_title = title.replace('###Human:\n', '').replace('###Human: ', '').replace('###Human:', '').strip()
        new_description = description.replace('###Assistant:\n', '').replace('###Assistant: ', '').replace('###Assistant:', '').strip()

        if new_title != title or new_description != description:
            rule['title'] = new_title
            rule['description'] = new_description
            cleaned_count += 1

    with open(RULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Cleaned {cleaned_count} rules.")

if __name__ == "__main__":
    clean_rules()
