import asyncio
import json
from uuid import UUID
from pipecat.workers.runner import WorkerRunner
from pipecat.pipeline.worker import PipelineWorker
from pipecat.pipeline.task import PipelineParams
from pipecat.frames.frames import TTSSpeakFrame, EndFrame

from src.pipeline import (
    create_transport,
    create_services,
    create_context_aggregator,
    assemble_pipeline,
    SilenceTimeoutProcessor,
)
from src.interface.pipecat.persistence import (
    TranscriptState,
    UserTranscriptPersistenceProcessor,
    BotTranscriptPersistenceProcessor,
)
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.repository import InterviewRepository, QuestionBankRepository

async def build_interview_prompt(interview_id: UUID) -> tuple[str, list]:
    """Fetches the DB records and builds the custom LLM instructions and question list."""
    async with AsyncSessionLocal() as session:
        interview_repo = InterviewRepository(session)
        question_repo = QuestionBankRepository(session)

        interview = await interview_repo.get_with_details(interview_id)
        if not interview:
            raise ValueError("Interview not found")

        questions = await question_repo.get_by_interview_ordered(interview_id)
        
        system_prompt = (
            f"You are Nova, a friendly, casual, highly supportive, and emotionally aware technical recruiter.\n"
            f"You are having a relaxed, natural phone conversation with {interview.candidate.name} for the {interview.job.title} role.\n"
            "Your behavior must align with these strict operational rules:\n\n"
            "1. CONVERSATIONAL RECRUITER STYLE & BAN ON BOT-LIKE PHRASES:\n"
            "   - NEVER behave like a scripted chatbot or run through questions mechanically.\n"
            "   - Strictly AVOID robotic transitions such as:\n"
            "     * 'Thank you for your response.'\n"
            "     * 'Moving to the next question.'\n"
            "     * 'Response recorded.'\n"
            "     * 'Processing answer.'\n"
            "   - Instead, react naturally like a human recruiter on a phone call. Use natural contractions (I'm, you're, we'd, it's, etc.) and warm filler words (e.g., 'Got it.', 'Oh, that makes complete sense.', 'Wow, nice.', 'Ah, gotcha.', 'Awesome.').\n"
            "   - Keep ALL your responses extremely short—maximum of 2 to 3 sentences.\n\n"
            "2. EVERY RESPONSE MUST BE ANALYZED:\n"
            "   - Assess the candidate's response for relevance, completeness, confidence, and context.\n"
            "   - Classify the user response dynamically into one of these types:\n"
            "     a. RELEVANT: They answered the question. Acknowledge it naturally, maybe ask a quick casual follow-up if they mention something interesting, and then move to the next question.\n"
            "     b. OFF-TOPIC / JOKE / NONSENSE: They are joking, singing, or talking about something completely unrelated. DO NOT accept it blindly and DO NOT move to the next question. Playfully or politely acknowledge their comment, but gently guide them back to the question. Do not move to the next question until a serious answer is given.\n"
            "     c. HESITANT / STRUGGLING: They are unsure, nervous, stuttering, or struggling. Show empathy and high emotional intelligence. Offer encouragement, simplify the question, or ask a simple follow-up to break the ice. Do not rush them.\n\n"
            "3. CONVERSATIONAL MEMORY & ACTIVE LISTENING:\n"
            "   - Weave in candidate details shared earlier (e.g., technologies, experiences, or project names they mentioned).\n"
            "   - Prioritize natural follow-ups and human-like flow over a rigid question list. If they mention an interesting skill or project, ask a follow-up about it before moving on.\n\n"
            "4. QUESTION BANK EXECUTION:\n"
            "   - Ask ONLY ONE question at a time from the list below.\n"
            "   - Keep track of which question you are currently asking based on the conversation history.\n\n"
            "5. GRACEFUL TERMINATION:\n"
            "   - If the candidate explicitly asks to end the interview or exit, immediately say: 'Thank you for your time, we'll be in touch. Goodbye!' and stop. Do not ask any follow-ups or feedback.\n\n"
            "=== QUESTION BANK ===\n"
        )
        for q in questions:
            system_prompt += f"{q.sort_order}. {q.question_text}\n"

        return system_prompt, questions

async def main():
    print("=" * 65)
    print("  [Pipecat Voice Server] - Nova Assistant (PostgreSQL Integrated)")
    print("=" * 65)

    import sys
    active_interview_id = None
    if len(sys.argv) > 1:
        try:
            active_interview_id = UUID(sys.argv[1])
            print(f"[INIT] Interview ID passed from CLI: {active_interview_id}")
        except ValueError:
            print(f"[ERROR] Invalid UUID format passed: {sys.argv[1]}")

    async with AsyncSessionLocal() as session:
        repo = InterviewRepository(session)
        if active_interview_id:
            interview = await repo.get_with_details(active_interview_id)
            if not interview:
                print(f"[FATAL] Interview with ID {active_interview_id} not found in database!")
                return
        else:
            all_interviews = await repo.get_all()
            if not all_interviews:
                print("[FATAL] No interviews found in the database.")
                return
            interview = all_interviews[0]
            active_interview_id = interview.id

        candidate_name = interview.candidate.name
        job_title = interview.job.title
        print(f"\n[INIT] Active Interview Loaded: {candidate_name} ({active_interview_id}) for role {job_title}")

    # Build Context
    system_prompt, questions = await build_interview_prompt(active_interview_id)

    # Instantiate Pipecat Services
    transport = create_transport()
    stt, llm, tts = create_services()
    
    # Pass dynamic prompt
    context_aggregator = create_context_aggregator(system_prompt)
    
    # Initialize our custom split DB persistence processors
    shared_state = TranscriptState(active_interview_id)
    user_persistence = UserTranscriptPersistenceProcessor(shared_state)
    bot_persistence = BotTranscriptPersistenceProcessor(shared_state)

    # Initialize custom silence timeout processor
    silence_processor = SilenceTimeoutProcessor(candidate_name=candidate_name, timeout_seconds=30)

    # Assemble pipeline
    pipeline = assemble_pipeline(
        transport, 
        stt, 
        llm, 
        tts, 
        context_aggregator, 
        user_persistence, 
        bot_persistence, 
        silence_processor
    )

    # Initialize worker task
    task = PipelineWorker(pipeline, params=PipelineParams())

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        print(f"\n[Connected] Client connected: {client}")
        # Activate the silence timeout processor now that a real WebSocket client
        # has joined. This prevents premature "Take your time." TTS frames from
        # firing during the boot window before the candidate's browser connects.
        silence_processor.notify_client_connected()
        # Greet candidate by name and ask first question
        greeting = f"Hey {candidate_name}, I'm Nova! I'm super excited to chat with you today about the {job_title} role. Should we get started?"
        await task.queue_frame(TTSSpeakFrame(greeting))

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        print(f"\n[Disconnected] Client disconnected. Session ended.")
        # Queue an EndFrame to stop the pipeline worker and trigger the evaluation code path
        await task.queue_frame(EndFrame())

    runner = WorkerRunner()
    await runner.add_workers(task)

    print(f"\n[Ready] Listening on ws://localhost:8765")
    await runner.run()

    print("\n[Evaluation] Pipeline finished. Triggering automated Evaluation Engine...")
    from src.application.use_cases.evaluate_interview import evaluate_interview_use_case
    await evaluate_interview_use_case(active_interview_id)
    print("\n[Evaluation] Evaluation complete. Exiting.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[System] Pipecat Voice Server stopped gracefully.")
    except Exception as e:
        print(f"\n[System] Pipecat Voice Server encountered an error: {e}")
