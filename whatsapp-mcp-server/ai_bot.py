import time
from datetime import datetime, timezone
import os
import json
import torch
from peft import PeftModel, PeftConfig
from transformers import AutoTokenizer, AutoModelForCausalLM
from whatsapp import (
    list_chats,
    list_messages,
    send_message,
    Message
)

# 🔧 Config
GROUP_NAME = "SRH Forever 🔥"
CONTACT_NAME = "18322089219"

# 📁 Persistence for seen messages
SEEN_FILE = "seen.json"

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_ids, f)

# 📁 Load PEFT model + adapter
base_dir = os.path.dirname(os.path.abspath(__file__))
adapter_path = os.path.abspath(os.path.join(base_dir, "../training_data/trained_ai_duplicate"))

peft_config = PeftConfig.from_pretrained(adapter_path, local_files_only=True, is_local=True)
base_model = AutoModelForCausalLM.from_pretrained(peft_config.base_model_name_or_path)
model = PeftModel.from_pretrained(base_model, adapter_path, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(peft_config.base_model_name_or_path)

# 🔍 Get JIDs based on name or number
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

# 🤖 Use model to generate response
def generate_reply(prompt):
    formatted = f"<|user|>{prompt}</s>\n<|assistant|>"
    inputs = tokenizer(formatted, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        do_sample=True,
        temperature=0.9,
        pad_token_id=tokenizer.eos_token_id
    )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return decoded.split("<|assistant|>")[-1].strip()

# 🧠 Poll database for incoming messages
def main():
    target_jids = get_target_chat_jids(GROUP_NAME, CONTACT_NAME)

    if not target_jids:
        print("❌ No target chats found.")
        return

    print("✅ Auto-replying to:")
    for jid in target_jids:
        print(f"  ➤ {jid}")

    last_seen_ids = load_seen_ids()

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

                # Skip old messages (optional)
                if (datetime.now(timezone.utc) - msg_time).total_seconds() > 30:
                    print("⏩ Skipping old message.")
                    last_seen_ids[jid] = msg_id
                    save_seen_ids(last_seen_ids)
                    continue

                # Skip if already seen
                if msg_id == last_seen_ids.get(jid):
                    continue

                print(f"📨 New message from {sender}: {msg_text}")
                t1 = time.time()

                reply = generate_reply(msg_text)
                t2 = time.time()

                if not reply.strip():
                    print("⚠️ Empty reply. Skipping.")
                    last_seen_ids[jid] = msg_id
                    save_seen_ids(last_seen_ids)
                    continue

                print(f"🤖 Reply generated: {reply}")

                success, status_msg = send_message(jid, reply)
                t3 = time.time()

                print(f"📤 Sent to {jid} | Success: {success} | Info: {status_msg}")
                print(f"""⏱️ Timing:
    DB fetch:    {t1 - t0:.2f}s
    Generation:  {t2 - t1:.2f}s
    Send:        {t3 - t2:.2f}s
    Total:       {t3 - t0:.2f}s
""")

                last_seen_ids[jid] = msg_id
                save_seen_ids(last_seen_ids)
                time.sleep(1)

            time.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
