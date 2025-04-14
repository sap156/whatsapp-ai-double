import time
import os
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from whatsapp import (
    list_chats,
    list_messages,
    send_message
)

# Load environment variables (for OpenAI key if needed later)
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set target group name
GROUP_NAME = "SRH Forever 🔥"

# Load your fine-tuned model from local directory
model_path = "trained_ai_duplicate"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path)
pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)

# Lookup WhatsApp group JID from name
def get_group_jid(name):
    chats = list_chats()
    for chat in chats:
        if chat["name"].strip().lower() == name.strip().lower():
            return chat["jid"]
    return None

# Generate AI reply from model
def generate_reply(prompt):
    formatted = f"<|user|>{prompt}</s>\n<|assistant|>"
    response = pipe(formatted, max_new_tokens=100, do_sample=True)[0]["generated_text"]
    return response.split("<|assistant|>")[1].strip()

# Main loop to monitor messages and auto-reply
def main():
    group_jid = get_group_jid(GROUP_NAME)
    if not group_jid:
        print(f"❌ Group '{GROUP_NAME}' not found.")
        return

    print(f"✅ Auto-replying in group '{GROUP_NAME}' (JID: {group_jid})...")
    last_seen_id = None

    while True:
        try:
            messages = list_messages(chat_jid=group_jid, limit=1)
            if not messages:
                time.sleep(3)
                continue

            msg = messages[0]
            msg_id = msg["id"]
            msg_text = msg.get("message", "")
            sender = msg.get("sender_name", "Someone")

            if msg_id == last_seen_id:
                time.sleep(3)
                continue

            print(f"📨 New message from {sender}: {msg_text}")
            reply = generate_reply(msg_text)
            send_message(group_jid, reply)
            print(f"🤖 Replied: {reply}")

            last_seen_id = msg_id
            time.sleep(3)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
