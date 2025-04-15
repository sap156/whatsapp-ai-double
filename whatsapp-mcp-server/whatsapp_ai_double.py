import time
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
import openai
from openai import OpenAI

from whatsapp import (
    list_chats,
    list_messages,
    send_message,
    Message
)

# === CONFIG ===
GROUP_NAME = "Group Name"     # Your Group Name Or None
CONTACT_NAME = "None"     # Contact number or None (just number, no +)
SEEN_FILE = "seen.json"

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

# === Find Target Chat JIDs ===
def get_target_chat_jids(group_name=None, contact_number=None):
    chats = list_chats()
    target_jids = []

    for chat in chats:
        name = chat.name.strip().lower()
        jid = chat.jid

        if group_name and name == group_name.strip().lower():
            target_jids.append(jid)
        elif contact_number and jid.startswith(f"{contact_number}@s.whatsapp.net"):
            target_jids.append(jid)

    if not group_name and not contact_number:
        target_jids = [chat.jid for chat in chats]

    return target_jids

# === OpenAI Response Generator ===
def generate_openai_reply(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Abhinav. Respond in witty, sarcastic Tenglish (Telugu + English)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ OpenAI error: {e}")
        return None

# === Main Bot Loop ===
def main():
    target_jids = get_target_chat_jids(GROUP_NAME, CONTACT_NAME)

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
                t0 = time.time()
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

                # Already seen
                if msg_id in seen_ids:
                    continue

                # Old message
                if (datetime.now(timezone.utc) - msg_time).total_seconds() > 30:
                    print("⏩ Skipping old message.")
                    seen_ids.add(msg_id)
                    save_seen_ids(seen_ids)
                    continue

                print(f"📨 New message from {sender}: {msg_text}")
                t1 = time.time()

                reply = generate_openai_reply(msg_text)
                t2 = time.time()

                if not reply or len(reply.strip()) < 3:
                    print("⚠️ No usable reply from OpenAI. Skipping.")
                    seen_ids.add(msg_id)
                    save_seen_ids(seen_ids)
                    continue

                print(f"🤖 Reply (OpenAI): {reply}")

                success, status_msg = send_message(jid, reply)
                t3 = time.time()

                print(f"📤 Sent to {jid} | Success: {success} | Info: {status_msg}")
                print(f"""⏱️ Timing:
    Fetch:       {t1 - t0:.2f}s
    Generation:  {t2 - t1:.2f}s
    Send:        {t3 - t2:.2f}s
    Total:       {t3 - t0:.2f}s
""")

                seen_ids.add(msg_id)
                save_seen_ids(seen_ids)
                time.sleep(1)

            time.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
