
import time
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI
from whatsapp import (
    list_chats,
    list_messages,
    send_message,
    Message
)

# === CONFIG ===
GROUP_NAMES = ["SRH Forever 🔥", "None"]     # List of group names
CONTACT_NUMBERS = ["1832200000", "None"] # List of contact numbers (just numbers)
SEEN_FILE = "seen.json"
MEMORY_FILE = "memory.json"
RESPONSE_DELAY = 3

# === Load ENV ===
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Seen Message Tracking ===
def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f).get("seen", []))
    return set()

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        json.dump({"seen": list(seen_ids)}, f)

# === Memory Handling ===
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

conversation_memory = load_memory()

# === Get All Matching JIDs ===
def get_target_chat_jids(group_names=None, contact_numbers=None):
    chats = list_chats()
    target_jids = []

    group_names = [g.lower().strip() for g in (group_names or [])]
    contact_numbers = [c.strip() for c in (contact_numbers or [])]

    for chat in chats:
        name = (chat.name or "").lower().strip()
        jid = chat.jid

        if any(name == g for g in group_names):
            target_jids.append(jid)
        elif any(jid.startswith(f"{c}@s.whatsapp.net") for c in contact_numbers):
            target_jids.append(jid)

    if not group_names and not contact_numbers:
        target_jids = [chat.jid for chat in chats]

    return target_jids

# === OpenAI Response Generator with Persistent Memory ===
def generate_openai_reply(prompt, jid):
    history = conversation_memory.get(jid, [])
    messages = [
        
        # {"role": "system", "content": "You are Abhinav. Start casually, reply in witty, sarcastic Tenglish (Telugu + English) tone. Be funny, not formal."},
        # {"role": "system", "content": "You are Abhinav. Start the conversation casually and then respond in witty, sarcastic Tenglish (Telugu + English) tone. Be funny and engaging. Avoid being too formal."},
        {"role": "system", "content": "You are Abhinav. Respond in casually, with a formal Higlish (Hindi + English) tone. Be funny and engaging. Avoid being too formal."},
     
    ]

    # Add recent memory
    messages += history[-5:]
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )

        reply = response.choices[0].message.content.strip()

        # Update + save memory
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})
        conversation_memory[jid] = history[-10:]
        save_memory(conversation_memory)

        return reply
    except Exception as e:
        print(f"⚠️ OpenAI error: {e}")
        return None

# === Main Loop ===
def main():
    target_jids = get_target_chat_jids(GROUP_NAMES, CONTACT_NUMBERS)

    if not target_jids:
        print("❌ No target chats found.")
        return

    print("✅ Auto-replying to:")
    for jid in target_jids:
        print(f"  ➤ {jid}")

    seen_ids = load_seen_ids()

    while True:
        try:
            for jid in target_jids:
                messages = list_messages(chat_jid=jid, limit=5, include_context=False)

                if not messages or not isinstance(messages[0], Message):
                    continue

                messages = [m for m in messages if not m.is_from_me]
                if not messages:
                    continue

                msg = messages[0]
                msg_id = getattr(msg, "id", None)
                msg_text = getattr(msg, "content", "")
                sender = getattr(msg, "sender", "Unknown")
                msg_time = getattr(msg, "timestamp", datetime.now(timezone.utc))

                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=timezone.utc)

                # Already seen or too old
                if msg_id in seen_ids or (datetime.now(timezone.utc) - msg_time).total_seconds() > 30:
                    seen_ids.add(msg_id)
                    save_seen_ids(seen_ids)
                    continue

                print(f"📨 {sender}: {msg_text}")
                time.sleep(RESPONSE_DELAY)

                reply = generate_openai_reply(msg_text, jid)

                if not reply or len(reply.strip()) < 3:
                    seen_ids.add(msg_id)
                    save_seen_ids(seen_ids)
                    continue

                success, status_msg = send_message(jid, reply)
                if success:
                    print(f"🤖 Sent reply: {reply}")

                seen_ids.add(msg_id)
                save_seen_ids(seen_ids)

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
       

          
    