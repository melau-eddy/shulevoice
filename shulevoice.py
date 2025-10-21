import firebase_admin
from firebase_admin import credentials, firestore
from vosk import Model, KaldiRecognizer
import pyaudio
import json
from espeakng import ESpeakNG
import requests
import os
from datetime import datetime

# Initialize Firebase Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate("/home/george/Desktop/shuleproject/firebase-key.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Setup Vosk and eSpeak
vosk_model_path = "/home/george/Desktop/shuleproject/vosk-model-small-en-us-0.15"  # Verify this path
model = Model(vosk_model_path)
rec = KaldiRecognizer(model, 16000)
es = ESpeakNG()

# Audio setup
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)

# Grok API setup
API_KEY = os.getenv("XAI_API_KEY")  # Set in ~/.bashrc: export XAI_API_KEY="your_key_here"
API_URL = "https://api.x.ai/v1/chat/completions"
SYSTEM_PROMPT = "You are ShuleVoice, a kind teacher for young kids in rural Kenya primary schools. Teach English, Math, or Science through fun, simple questions and explanations. Ask one question at a time, evaluate answers nicely, adapt difficulty, and keep responses short, spoken-friendly, and encouraging. Align to early-grade topics."

# Conversation history (for context across turns)
history = [{"role": "system", "content": SYSTEM_PROMPT}]

# Function to check internet connectivity
def has_internet():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        return False

# Function to get Grok API response
def get_grok_response(user_input):
    if not API_KEY:
        return "API key not set. Check your environment variable."
    
    messages = history + [{"role": "user", "content": user_input}]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "grok-beta",  # Use "grok-4" if subscribed
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": content})
            if len(history) > 12:  # Limit to system + 10 messages
                history = [history[0]] + history[-10:]
            return content
        else:
            return f"API error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Request failed: {str(e)}"

# Function to log progress to Firestore
def log_progress(student_id, topic, user_input, ai_response, correct=None, time_spent=0):
    try:
        doc_ref = db.collection('progress').document()
        doc_ref.set({
            'student_id': student_id,
            'timestamp': datetime.utcnow().isoformat(),
            'topic': topic,
            'user_input': user_input,
            'ai_response': ai_response,
            'correct': correct,
            'time_spent': time_spent
        })
        print(f"Logged progress for {student_id} in {topic}")
    except Exception as e:
        print(f"Firestore error: {str(e)}")

# Main Loop
es.say("Hello! I'm ShuleVoice. Say 'start math', 'start english', or 'start science' to begin, or say your student ID first.")
current_topic = None
student_id = None
start_time = None

stream.start_stream()
while True:
    data = stream.read(4000, exception_on_overflow=False)
    if rec.AcceptWaveform(data) and rec.Result():
        result = json.loads(rec.Result())
        text = result.get("text", "").lower().strip()
        if text:
            if not student_id and "student" in text:
                student_id = text.replace("student", "").strip() or "unknown"
                es.say(f"Welcome, Student {student_id}! Say 'start math', 'start english', or 'start science' to begin.")
                continue
            elif "start" in text and student_id:
                current_topic = text.replace("start ", "")
                start_time = datetime.now()
                response = f"Great! Let's start {current_topic}. What's your first answer or question?"
            elif current_topic and student_id:
                if not start_time:
                    start_time = datetime.now()
                user_input = f"In {current_topic} lesson: {text}"
                response = get_grok_response(user_input)
                time_spent = (datetime.now() - start_time).seconds if start_time else 0
                correct = "correct" in response.lower()  # Simple heuristic
                log_progress(student_id, current_topic, text, response, correct, time_spent)
                start_time = datetime.now()  # Reset for next interaction
            else:
                response = "Please say your student ID or start a topic first."
            
            es.say(response)
            print(f"User: {text}\nGrok: {response}\n")