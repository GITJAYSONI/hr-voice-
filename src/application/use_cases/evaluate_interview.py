import json
from uuid import UUID
from groq import Groq

from src import config
from src.application.schemas import StructuredEvaluation
from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.models import Evaluation
from src.infrastructure.db.repository import (
    InterviewRepository,
    InterviewResponseRepository,
    EvaluationRepository,
    VisionMetricRepository
)
from src.utils.pdf_generator import create_evaluation_pdf

groq_client = Groq(api_key=config.GROQ_API_KEY)

async def evaluate_interview_use_case(interview_id: UUID) -> None:
    """
    Grades the candidate based on their transcripts and vision metrics,
    generates a PDF report, and stores it in the database.
    """
    async with AsyncSessionLocal() as session:
        interview_repo = InterviewRepository(session)
        response_repo = InterviewResponseRepository(session)
        eval_repo = EvaluationRepository(session)
        vision_repo = VisionMetricRepository(session)

        # 1. Fetch data
        interview = await interview_repo.get_with_details(interview_id)
        if not interview:
            print(f"[Evaluation] Error: Interview {interview_id} not found.")
            return

        transcripts = await response_repo.get_by_interview(interview_id)
        if not transcripts:
            print(f"[Evaluation] Error: No transcripts found for interview {interview_id}. Skipping evaluation.")
            return

        vision_metrics = await vision_repo.get_by_interview(interview_id)

        # 2. Build Transcript Block
        transcript_text = ""
        for t in transcripts:
            transcript_text += f"[Bot]: {t.bot_transcript}\n[Candidate]: {t.candidate_transcript}\n\n"

        # 2b. Aggregate Vision Metrics
        avg_eye_contact = 0.0
        avg_posture = 0.0
        presence_rate = 1.0
        distractions = 0
        cheating_events = 0
        if vision_metrics:
            avg_eye_contact = sum(float(m.eye_contact_score or 0) for m in vision_metrics) / len(vision_metrics)
            avg_posture = sum(float(m.posture_score or 0) for m in vision_metrics) / len(vision_metrics)
            presence_rate = sum(1 if m.presence_detected else 0 for m in vision_metrics) / len(vision_metrics)
            distractions = sum(1 if m.distraction_event else 0 for m in vision_metrics)
            cheating_events = sum(1 if m.potential_cheating else 0 for m in vision_metrics)

        vision_summary = (
            f"Eye Contact Gaze Accuracy: {avg_eye_contact * 100:.1f}%\n"
            f"Posture Alignment Score: {avg_posture * 100:.1f}%\n"
            f"Candidate Presence Rate: {presence_rate * 100:.1f}%\n"
            f"Distraction Incidents: {distractions}\n"
            f"Potential Cheating Incidents: {cheating_events}\n"
        )

        # 3. Build Prompt
        system_prompt = (
            "You are an expert Senior Engineering Manager evaluating a candidate's technical interview transcript and visual behavior metrics.\n"
            "You must grade their performance based on both the transcript and the provided visual metrics.\n"
            "Output ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "technical_score": 0-100,\n'
            '  "communication_score": 0-100,\n'
            '  "behavioral_score": 0-100,\n'
            '  "vision_score": 0-100,\n'
            '  "overall_score": 0-100,\n'
            '  "feedback": "Detailed paragraph explaining the scores",\n'
            '  "recommendation": "Hire", "Hold", or "Reject"\n'
            "}"
        )

        user_prompt = (
            f"=== JOB TARGET ===\nTitle: {interview.job.title}\nDescription: {interview.job.description_text}\n\n"
            f"=== INTERVIEW TRANSCRIPT ===\n{transcript_text}\n"
            f"=== CANDIDATE VISION & BEHAVIOR METRICS ===\n{vision_summary}\n"
        )

        print("[Evaluation] Sending transcript and vision metrics to Groq LLM for grading...")

        # 4. Call LLM
        response = groq_client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        raw_json = response.choices[0].message.content

        # 5. Parse JSON
        try:
            data_dict = json.loads(raw_json)
            parsed_eval = StructuredEvaluation.model_validate(data_dict)
        except Exception as e:
            print(f"[Evaluation] Failed to parse LLM structured output: {e}\nRaw output: {raw_json}")
            return

        print(f"[Evaluation] Scored {parsed_eval.overall_score}/100. Recommendation: {parsed_eval.recommendation}")

        # 6. Generate PDF Bytes
        pdf_bytes = create_evaluation_pdf(
            candidate_name=interview.candidate.name,
            job_title=interview.job.title,
            tech_score=parsed_eval.technical_score,
            comm_score=parsed_eval.communication_score,
            behavior_score=parsed_eval.behavioral_score,
            vision_score=parsed_eval.vision_score,
            overall_score=parsed_eval.overall_score,
            feedback=parsed_eval.feedback,
            recommendation=parsed_eval.recommendation
        )

        # 7. Save to Database
        evaluation_entity = Evaluation(
            interview_id=interview_id,
            overall_score=float(parsed_eval.overall_score),
            technical_score=float(parsed_eval.technical_score),
            communication_score=float(parsed_eval.communication_score),
            behavioral_score=float(parsed_eval.behavioral_score),
            vision_score=float(parsed_eval.vision_score),
            summary=parsed_eval.feedback,
            recommendation=parsed_eval.recommendation,
            pdf_report=pdf_bytes
        )
        await eval_repo.add(evaluation_entity)
        
        # Update interview status
        interview.status = "evaluated"
        await interview_repo.commit()
        print(f"[Evaluation] PDF Report generated and saved to database successfully!")

