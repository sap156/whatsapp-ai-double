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
    Message,
    get_contact_chats
)

# === CONFIG ===
GROUP_NAMES = ["SRH Forever 🔥", "None"]     # List of group names
CONTACT_NUMBERS = ["16146029714", "18322089219","918008444196"]     # List of contact numbers (just numbers)
SEEN_FILE = "seen.json"
MEMORY_FILE = "memory.json"
TONE_FILE = "tone_map.json"
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

def load_tone_map():
    if os.path.exists(TONE_FILE):
        with open(TONE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tone_map(tone_map):
    with open(TONE_FILE, "w") as f:
        json.dump(tone_map, f, indent=2)

tone_map = load_tone_map()

# === Generate Custom Tone Prompt ===
def generate_tone_prompt(jid):
    chats = get_contact_chats(jid, limit=100) # Fetch the last 100 messages
    messages = [chat.last_message for chat in chats if chat.last_is_from_me and chat.last_message]

    if not messages:
        return "You are Abhinav. Respond casually with wit and sarcasm in Tenglish."

    prompt = (
        "Based on the following WhatsApp messages by Abhinav, "
        "Analyze his personality and tone **when talking to this specific contact**. "
        "Reply with a concise system prompt (in one sentence) that tells an AI assistant "
        "How to respond **like Abhinav would to this person**, based on his language, style, emojis, slang, and behavior. "
        "**Return only the instruction, no explanation.**\n\n"
        + "\n".join(messages[:50]) # Limit to the last 50 messages
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Tone analysis failed: {e}")
        return "You are Abhinav. Respond casually with wit and sarcasm in Tenglish."

# === Bootstrapping memory from history ===
def initialize_memory_from_history(jid):
    history = []
    chat_history = get_contact_chats(jid, limit=10)

    for chat in reversed(chat_history):
        role = "assistant" if chat.last_is_from_me else "user"
        content = chat.last_message or ""
        if content.strip():
            history.append({"role": role, "content": content.strip()})

    return history[-10:]

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

# === OpenAI Response Generator with Persistent Memory & Tone ===
def generate_openai_reply(prompt, jid):
    if jid not in conversation_memory:
        conversation_memory[jid] = initialize_memory_from_history(jid)

    history = conversation_memory.get(jid, [])

    if jid not in tone_map:
        tone_map[jid] = generate_tone_prompt(jid)
        save_tone_map(tone_map)

    messages = [{"role": "system", "content": tone_map[jid]}]
    messages += history[-10:]
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )

        reply = response.choices[0].message.content.strip()

        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": reply})
        conversation_memory[jid] = history[-25:]
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
