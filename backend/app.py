from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai
import os
import random
from collections import defaultdict, deque

from prediction_model import predict_alzheimer

# -----------------------------
# Setup
# -----------------------------
load_dotenv()
app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_AVAILABLE = False
model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        GEMINI_AVAILABLE = True
    except Exception as e:
        print(f"Error configuring Gemini: {e}")

# -----------------------------
# Symptoms
# -----------------------------
SYMPTOMS = [
    "Dizziness",
    "Low_Energy",
    "Drowsiness",
    "Vision_Problems",
    "Headache",
    "Palpitations",
    "Chest_Pain",
    "Urinary_Discomfort",
    "Urinary_Frequency",
    "Insomnia",
    "Depressed_Mood",
    "Crying_Spells",
    "Elevated_Mood",
    "Wandering",
    "Falls",
]
SYMPTOM_KEYWORDS = {
    "Headache": ["headache", "migraine"],
    "Dizziness": ["dizzy", "dizziness", "lightheaded"],
    "Low_Energy": ["low energy", "fatigue", "tired"],
    "Drowsiness": ["sleepy", "drowsy", "excessive sleep"],
    "Vision_Problems": ["vision", "blurry eyes", "sight issues"],
    "Palpitations": ["palpitations", "rapid heartbeat"],
    "Chest_Pain": ["chest pain"],
    "Urinary_Discomfort": ["urinary discomfort", "pain urinating"],
    "Urinary_Frequency": ["pee a lot", "urinate frequently"],
    "Insomnia": ["insomnia", "trouble sleeping"],
    "Depressed_Mood": ["depressed", "sad"],
    "Crying_Spells": ["crying", "tearful"],
    "Elevated_Mood": ["manic", "too happy"],
    "Wandering": ["wandering", "getting lost"],
    "Falls": ["fall", "fallen"],
}


# -----------------------------
# Helpers
# -----------------------------
def extract_yes_no_from_response(response: str):
    if not response:
        return None
    text = response.lower().strip()
    if any(p in text for p in ["yes", "yeah", "yep", "sure", "correct", "true", "y"]):
        return True
    if any(n in text for n in ["no", "nope", "never", "false", "n"]):
        return False
    return None


def detect_multiple_symptoms(user_message: str):
    found = []
    msg = user_message.lower()
    # Check keyword mappings
    for symptom, keywords in SYMPTOM_KEYWORDS.items():
        if any(k in msg for k in keywords):
            found.append(symptom)

    # 🔹 Also check if the user directly typed a symptom name
    for symptom in SYMPTOMS:
        if symptom.replace("_", " ").lower() in msg:
            found.append(symptom)

    return list(set(found))


def generate_symptom_question(symptom: str, display_index: int) -> str:
    """Generate a natural, unique symptom question using Gemini (no fallback)."""
    if not GEMINI_AVAILABLE or not model:
        raise RuntimeError("Gemini is not available for question generation")

    prompt = f"""
You are a medical assistant. Generate a natural, empathetic question asking about this symptom:
- Symptom: {symptom.replace('_', ' ')}
- Make it short (under 12 words)
- Make it different each time
- End with "(yes/no)"
- Return only the question, no bullets
- Include the index at the END in this format: "(yes/no) {display_index + 1}/{len(SYMPTOMS)}"
"""
    resp = model.generate_content(prompt)
    if hasattr(resp, "text") and resp.text:
        lines = [line.strip() for line in resp.text.split("\n") if line.strip()]
        if lines:
            return random.choice(lines)

    # If Gemini outputs nothing, force an exception
    raise RuntimeError(f"Gemini failed to generate a question for {symptom}")


def ask_gemini_info(user_message, focus_symptom=None):
    if GEMINI_AVAILABLE and model:
        try:
            prompt = f"""
You are a medical assistant.

User asked: "{user_message}"

Answer briefly (1–2 lines):
- If user mentions "{focus_symptom or 'a symptom'}", explain if it is related to Alzheimer's or not."
"""
            resp = model.generate_content(prompt)
            if hasattr(resp, "text") and resp.text:
                return resp.text.strip()
        except:
            return "⚠️ Not a diagnosis."
    return "⚠️ Not a diagnosis."


# -----------------------------
# Routes
# -----------------------------
@app.route("/api/extract-symptoms", methods=["POST"])
def extract_symptoms():
    data = request.json or {}
    conversation = data.get("conversation", [])
    stage = data.get("assessment_stage", "initial")
    current_index = int(data.get("current_symptom_index", 0) or 0)
    answered = data.get("answered", {}) or {}

    # Find the latest user message
    user_message = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            user_message = msg.get("text", "")
            break

    # 1️⃣ Greeting
    if stage == "initial":
        return jsonify({
            "success": True,
            "assessment_stage": "qa",
            "answer": "Hello, I'm your Alzheimer's Health Assistant 🤖. How can I help you today?"
        })

    # 2️⃣ General Q&A
    if stage == "qa":
        focus = detect_multiple_symptoms(user_message)
        ans = ask_gemini_info(user_message, focus[0] if focus else None)
        return jsonify({
            "success": True,
            "assessment_stage": "precheck",
            "answer": ans,
            "next_question": "Are you worried about your health? (yes/no)"
        })

    # 3️⃣ Pre-check
    if stage == "precheck":
        user_yes_no = extract_yes_no_from_response(user_message)
        if user_yes_no:
            first_symptom = SYMPTOMS[0]
            question = generate_symptom_question(first_symptom, 0)
            return jsonify({
                "success": True,
                "assessment_stage": "symptom_qa",
                "question": question,
                "symptom": first_symptom,
                "current_symptom_index": 0,
                "answered": answered
            })
        else:
            return jsonify({
                "success": True,
                "assessment_stage": "qa",
                "answer": "Okay, I’ll keep answering Alzheimer’s-related questions as you ask me."
            })

    # 4️⃣ Symptom flow
    if stage == "symptom_qa":
        detected = detect_multiple_symptoms(user_message)
        confirmations = []

        # Record any directly mentioned symptoms
        for sym in detected:
            if sym not in answered:
                answered[sym] = True
                confirmations.append(sym.replace("_", " "))

        # Record current yes/no answer
        user_yes_no = extract_yes_no_from_response(user_message)
        current_symptom = SYMPTOMS[current_index]
        if user_yes_no is not None:
            answered[current_symptom] = user_yes_no

        # Optional: handle ambiguous answer
        elif current_symptom not in answered:
            answered[current_symptom] = False

        confirm_text = None
        if confirmations:
            confirm_text = f"✅ Got it, I’ll mark {', '.join(confirmations)} as symptoms you already have.\nLet’s continue."

        # Find next unanswered symptom
        next_index = None
        for i, s in enumerate(SYMPTOMS):
            if s not in answered:
                next_index = i
                break

        # If more symptoms remain
        if next_index is not None:
            next_symptom = SYMPTOMS[next_index]
            question = generate_symptom_question(next_symptom, next_index)
            return jsonify({
                "success": True,
                "assessment_stage": "symptom_qa",
                "question": question,
                "symptom": next_symptom,
                "current_symptom_index": next_index,
                "answered": answered,
                "confirmation": confirm_text
            })

        # If all answered
        return jsonify({
            "success": True,
            "assessment_stage": "done",
            "answer": "Thanks for answering all questions. Analyzing your responses…",
            "answered": answered,
            "next_stage": "open_conversation"
        })

    # Fallback
    return jsonify({
        "success": True,
        "assessment_stage": stage,
        "answer": "⚠️ Not a diagnosis."
    })
   


# -----------------------------
# Prediction
# -----------------------------
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.json or {}
    symptoms_selected = data.get("symptoms", [])
    symptoms_dict = {s: True for s in symptoms_selected}
    try:
        result = predict_alzheimer(symptoms_dict)
        return jsonify(
            {
                "success": True,
                "prediction": result,
                "next_stage": "open_conversation",
                "message": (
                    "Prediction complete. Let's continue talking about how you feel. "
                    "I am here to support you and discuss your concerns."
                ),
            }
        )
    except Exception as e:
        print("Prediction failed:", e)
        return jsonify({"success": False, "error": "Prediction failed ⚠️"}), 500


conversation_memory = defaultdict(lambda: deque(maxlen=45))


@app.route("/api/open-conversation", methods=["POST"])
def open_conversation():
    data = request.json or {}
    conversation = data.get("conversation", [])
    session_id = data.get("session_id", "default")  # unique ID per user/session
    user_message = ""

    # Find last user input
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            user_message = msg.get("text", "")
            break

    # Store user message in memory
    if user_message:
        conversation_memory[session_id].append({"role": "user", "text": user_message})

    # Build memory context (last 45 messages)
    memory_context = "\n".join(
        [
            f"{msg['role'].capitalize()}: {msg['text']}"
            for msg in conversation_memory[session_id]
        ]
    )

    # Default reply
    bot_reply = "⚠️ Server error. Please have Patience"

    if GEMINI_AVAILABLE and model:
        try:
            prompt = f"""
You are a compassionate therapist who supports patients and families dealing with Alzheimer's. 
You always communicate with warmth, patience, and reassurance, while keeping your answers practical and clear.
Do not use asterisks (*) for emphasis or bullet points. 
If listing options, use plain text with dashes (-) or numbers (1., 2., 3.). Or every option on separate line

{memory_context}

Guidelines for your response:
1. **Tone**: Empathetic, gentle, and supportive. Always validate the patient’s feelings.  
2. **Length**: 2–3 short sentences (not longer).  
3. **If the patient asks about symptoms**: explain simply, avoid medical jargon, and provide coping strategies or lifestyle tips.  
4. **If the patient asks about finding help/doctors**: give general steps (e.g., search local memory clinic, contact neurologist, ask family doctor for referral).  
5. **If the patient asks for options or choices like: **: provide a clear list or steps of 3 to 4 bullet points. Do not write them inline inside a paragraph.    
6. **Always end with a supportive next step** (e.g., encouraging them to talk to loved ones, seek professional guidance, or note down changes in symptoms).

"""
            resp = model.generate_content(prompt)
            if hasattr(resp, "text") and resp.text:
                bot_reply = resp.text.strip()
        except Exception as e:
            print("Gemini conversation error:", e)

    # Store bot reply in memory
    conversation_memory[session_id].append({"role": "bot", "text": bot_reply})

    return jsonify(
        {
            "success": True,
            "assessment_stage": "open_conversation",
            "answer": bot_reply,
            "memory_length": len(conversation_memory[session_id]),  # debug info
        }
    )

# -----------------------------
# Health check
# -----------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "healthy",
            "gemini": GEMINI_AVAILABLE,
            "symptoms_count": len(SYMPTOMS),
            "timestamp": str(datetime.now()),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
