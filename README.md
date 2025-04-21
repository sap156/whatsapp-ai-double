# 🤖 WhatsApp AI Double Powered by OpenAI + MCP

<img width="1021" alt="Screenshot 2025-04-21 at 10 12 18 AM" src="https://github.com/user-attachments/assets/959a06db-67e1-4490-bc2d-d93bdafdf7e0" />


Ever wondered what it would be like if your AI could reply to your friends *as you* on WhatsApp?

That's exactly what this project does.

This bot connects to the [WhatsApp-MCP](https://github.com/MervinPraison/WhatsApp-MCP) server, listens for messages from specific people or groups, and generates witty, personalized responses using OpenAI's GPT model.

---

## 🚀 Features

## 📦 Prerequisites

- Go >= 1.24
- Python >= 3.11
- pip
- SQLite3
- ffmpeg (optional, for audio message conversion)
- An OpenAI API key

- Replies to WhatsApp messages in real-time using OpenAI
- Supports both group chats and individual contacts
- Responds in your personal tone (witty, casual, sarcastic)
- Easy configuration via `.env`
- Logs processing time and errors

---

## 🛠️ Setup Instructions

### 1. Clone this Repo

```bash
git clone https://github.com/your-username/whatsapp-ai-double.git
cd whatsapp-ai-double
```

### 2. Setup the WhatsApp Bridge (Go)

```bash
cd whatsapp-bridge
go mod download
go run main.go
```

- Scan the QR code with your WhatsApp mobile app.
- Wait for "Connected to WhatsApp!".
- The bridge will sync messages to `whatsapp-bridge/store/messages.db` and start a REST API on `http://localhost:8080`.

### 3. Install Python Dependencies (MCP Server & AI Bot)

```bash
pip install httpx mcp[cli] requests python-dotenv openai
```

This installs dependencies for both the MCP CLI tools and the AI auto-responder.

### 4. Create a `.env` File

```env
OPENAI_API_KEY=your_openai_key_here
```

### 5. Configure the Bot

Open `whatsapp_ai_double.py` and update:

```python
GROUP_NAMES = "SRH Forever 🔥"       # Or set to None
CONTACT_NUMBERS = "183220XXXXX"       # Or set to None
```

You can:

- Set just `GROUP_NAMES` → only group messages will be responded to
- Set just `CONTACT_NUMBER` → only DMs will be replied to
- Set both → respond to both
- Set none → reply to all incoming messages

### 6. Run the Go Bridge and the AI Bot

```bash
# In one terminal, start the Go bridge (if not already running)
cd whatsapp-bridge
go run main.go

# In another terminal, start the AI auto-responder
cd whatsapp-mcp-server
python3 whatsapp_ai_double.py
```

You'll see logs like:

```
🚗 Auto-replying to:
  ➤ 1832XXXXX@s.whatsapp.net
  ➤ 9180XXXXXX-149527XXXXX8@g.us
📨 New message from 1832XXXXXX: How's it going?
🤖 Reply (OpenAI): Haha chill ra babu, just munching on some code 🍕
```

---

## 💡 How It Works

- Uses the MCP server to read from a local `messages.db` SQLite database
- Matches latest messages from target chats
- Generates a reply using OpenAI
- Sends reply via WhatsApp MCP's REST API

---

## 🧠 Want to Customize?

- Change the personality by editing the system prompt:

```python
{"role": "system", "content": "You are Abhinav, witty and sarcastic. Respond in Tenglish (Telugu + English)"}
```

- Add filters, memory, or even a context window

---

## 🧼 Clean Shutdown

Seen messages are stored in `seen.json`. If deleted, the bot may reprocess older messages.
Generated Tones are stored in `tone_map.json`. If deleted, the bot may reprocess older messages to find your tone.
Messages for context awareness are stored in `memory.json`. If deleted, the bot may reprocess older messages for context awareness. 

