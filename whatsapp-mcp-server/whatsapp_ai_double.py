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
    get_contact_chats,
    get_message_context
)

# === CONFIG ===
GROUP_NAMES = ["SRH Forever 🔥", "None"]
CONTACT_NUMBERS = ["161XXXXX", "18322XXXXX", "91800844XXX"]
SEEN_FILE = "seen.json"
MEMORY_FILE = "memory.json"
TONE_FILE = "tone_map.json"
RESPONSE_DELAY = 3
TONE_REFRESH_COUNT = 100

# === Load ENV ===
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Seen Tracking ===
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

# === Tone Handling ===
def load_tone_map():
    if os.path.exists(TONE_FILE):
        with open(TONE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_tone_map(tone_map):
    with open(TONE_FILE, "w") as f:
        json.dump(tone_map, f, indent=2)

tone_map = load_tone_map()

# === Generate Tone ===
def generate_tone_prompt(jid):
    chats = get_contact_chats(jid, limit=100)
    messages = [chat.last_message for chat in chats if chat.last_is_from_me and chat.last_message]

    if not messages:
        return "You are Abhinav. Respond casually with wit and sarcasm in Tenglish."

    prompt = (
        "Based on the following WhatsApp messages by Abhinav, "
        "analyze his personality and tone when talking to this contact. "
        "Write a one-sentence instruction to mimic his tone. Return only the instruction.\n\n"
        + "\n".join(messages[:50]) # Limit to 50 messages for analysis
        
    )

    try:
        response = OpenAI().chat.completions.create(
            model=os.getenv("OPENAI_MODEL_TONE", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Tone analysis failed: {e}")
        return "You are Abhinav. Respond casually with wit and sarcasm in Tenglish."

# === Bootstrap memory ===
def initialize_memory_from_history(jid):
    history = []
    chat_history = get_contact_chats(jid, limit=10)
    for chat in reversed(chat_history):
        role = "assistant" if chat.last_is_from_me else "user"
        content = chat.last_message or ""
        if content.strip():
            history.append({"role": role, "content": content.strip()})
    return history[-10:]

# === Target JIDs ===
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
    return target_jids if target_jids else [chat.jid for chat in chats]

# === Response Generator ===
def generate_openai_reply(prompt, jid, msg_id=None):
    if jid not in conversation_memory:
        conversation_memory[jid] = initialize_memory_from_history(jid)

    history = conversation_memory.get(jid, [])

    # Tone cache refresh
    tone_data = tone_map.get(jid, {})
    if not tone_data or tone_data.get("count", 0) >= TONE_REFRESH_COUNT:
        new_prompt = generate_tone_prompt(jid)
        tone_map[jid] = {"prompt": new_prompt, "count": 0}
        save_tone_map(tone_map)

    tone_map[jid]["count"] += 1
    save_tone_map(tone_map)

    # Short-term context from recent messages
    context = []
    if msg_id:
        recent = get_message_context(msg_id, before=3, after=0)
        for m in recent.before:
            if m.content.strip():
                role = "assistant" if m.is_from_me else "user"
                context.append({"role": role, "content": m.content.strip()})

    messages = [{"role": "system", "content": tone_map[jid]["prompt"]}] + context[-3:] + history[-10:] + [{"role": "user", "content": prompt}]

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_REPLY", "gpt-4o"),
            messages=messages,
            temperature=0.7,
            max_tokens=250
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

# === Main Bot Loop ===
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
                reply = generate_openai_reply(msg_text, jid, msg_id)
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
