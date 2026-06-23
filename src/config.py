import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/hr_interview")
SYNC_DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hr_interview")

# API Keys and Models
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

LLM_MODEL = "llama-3.3-70b-versatile"
STT_MODEL = "nova-2"
TTS_VOICE = "aura-luna-en"

# Bot Constants
WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765

# System Prompt for the AI agent
SYSTEM_PROMPT = """You are Nova, a friendly and helpful voice assistant built with Pipecat.
Keep your responses short and conversational — ideally 1-3 sentences.
You are being used to demonstrate how Pipecat's real-time voice pipeline works.
Be warm, helpful and a little enthusiastic. If asked about yourself, explain you are
a voice AI demo using Deepgram for speech recognition and text-to-speech, Groq Llama 3
for intelligence, and Pipecat to tie it all together."""

