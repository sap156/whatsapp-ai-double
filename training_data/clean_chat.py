import re
import json
import os

your_name = "Abhinav"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
chat_file = os.path.join(BASE_DIR, "_chat.txt")
output_file = os.path.join(BASE_DIR, "training_data.json")

with open(chat_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

conversations = []
current_prompt = ""
last_speaker = ""

# Updated regex for [6/5/23, 12:27:36 PM] Abhinav: message
pattern = r'^\[(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}:\d{2})[\u202f\s]?(AM|PM|am|pm)\] (.*?): (.*)'

for line in lines:
    match = re.match(pattern, line)
    if match:
        speaker = match.group(4)
        message = match.group(5).strip()

        if speaker != your_name:
            current_prompt = f"{speaker}: {message}\n"
            last_speaker = speaker
        else:
            if current_prompt:
                conversations.append({
                    "prompt": current_prompt.strip(),
                    "response": message
                })
                current_prompt = ""
    else:
        if last_speaker == your_name and conversations:
            conversations[-1]["response"] += " " + line.strip()
        elif current_prompt:
            current_prompt += " " + line.strip()

# Save the output
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(conversations, f, indent=2)

print(f"✅ Saved {len(conversations)} prompt-response pairs to {output_file}")
