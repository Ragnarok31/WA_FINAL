import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from flask_cors import CORS
from twilio.rest import Client as TwilioClient
from openai import OpenAI

# ─── Init ─────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
CORS(app)

# MongoDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

# WebSockets
socketio = SocketIO(app, cors_allowed_origins="*")

# Twilio (for sending back to WhatsApp users)
twilio = TwilioClient(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# OpenAI client—note updated to a non‐deprecated model
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── OpenAI Function Definitions ─────────────────
functions = [
    {
        "name": "summarize",
        "description": "Summarize text in 1–2 sentences.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        },
    },
    {
        "name": "translate",
        "description": "Translate text into a target language.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "targetLang": {"type": "string"}
            },
            "required": ["text", "targetLang"]
        },
    },
]

def call_openai(user_input: str) -> str:
    """Calls OpenAI with function-calling; returns the resulting text."""
    messages = [
        {"role":"system","content":"You have tools: summarize(text) and translate(text,targetLang)."},
        {"role":"user","content":user_input}
    ]
    res = openai.chat.completions.create(
        model="gpt-3.5-turbo",           # updated model
        messages=messages,
        functions=functions,
        function_call="auto"
    )
    msg = res.choices[0].message

    # If OpenAI decided to call a function, parse & run it
    if msg.function_call:
        name = msg.function_call.name
        args = json.loads(msg.function_call.arguments)
        if name == "summarize":
            text = args["text"]
            return text[:200] + ("…" if len(text) > 200 else "")
        elif name == "translate":
            return f"[{args['targetLang']}] {args['text']}"

    # Otherwise just return the content
    return msg.content or "(no content)"

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    sender = request.values.get("From")      # e.g. "whatsapp:+91..."
    body   = request.values.get("Body", "").strip()

    # 1) Process with OpenAI
    reply = call_openai(body)

    # 2) Log to MongoDB
    mongo.db.logs.insert_one({
        "from": sender,
        "in": body,
        "out": reply,
        "ts": datetime.utcnow()
    })

    # 3) Send back to WhatsApp via Twilio
    twilio.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=sender,
        body=reply
    )

    # 4) Broadcast to any WebSocket clients
    socketio.emit("new_message", {
        "from": sender,
        "body": body,
        "reply": reply
    })

    # 5) Return JSON so your frontend can pick it up
    return jsonify({
        "message_sent": body,
        "reply": reply
    }), 200

@socketio.on("connect")
def on_connect():
    emit("status", {"msg": "Connected to Flask-SocketIO"})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
