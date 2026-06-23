import json
import io
from uuid import UUID
from pypdf import PdfReader
from groq import AsyncGroq

from src import config
from src.application.schemas import GeneratedQuestions
from src.infrastructure.db.models import QuestionBank
from src.infrastructure.db.repository import QuestionBankRepository

groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts text from a binary PDF payload."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF resume: {e}")

async def generate_and_save_questions(
    interview_id: UUID,
    resume_bytes: bytes,
    job_description: str,
    question_repo: QuestionBankRepository,
    num_questions: int = 8
) -> None:
    """
    Extracts text from the resume, asks the Groq LLM to generate interview questions,
    and persists them to the PostgreSQL database.
    """
    # 1. Extract resume text
    resume_text = extract_text_from_pdf(resume_bytes)

    # 2. Build LLM Prompt
    system_prompt = (
        "You are an expert HR Technical Recruiter. Your task is to generate highly specific "
        "interview questions based on the provided Candidate Resume and Job Description.\n"
        f"You must generate exactly {num_questions} questions covering: technical, behavioral, situational, and communication.\n"
        "CRITICAL INSTRUCTION FOR QUESTION 1:\n"
        "The very first question MUST be about the candidate's most recent company found in their resume. Phrase it exactly like this:\n"
        "\"Can you describe the role and position you have worked in at {{Insert Latest Company Name}}, how long you have worked there, and what your responsibilities were?\"\n\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "questions": [\n'
        '    {"category": "technical", "question_text": "..."},\n'
        '    {"category": "behavioral", "question_text": "..."}\n'
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"=== JOB DESCRIPTION ===\n{job_description}\n\n"
        f"=== CANDIDATE RESUME ===\n{resume_text}\n"
    )

    # 3. Call Groq API in JSON mode
    response = await groq_client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    raw_json = response.choices[0].message.content
    
    # 4. Parse JSON using Pydantic
    try:
        data_dict = json.loads(raw_json)
        parsed_data = GeneratedQuestions.model_validate(data_dict)
    except Exception as e:
        raise ValueError(f"Failed to parse LLM structured output: {e}\nRaw output: {raw_json}")

    # 5. Save generated questions to Database
    for i, q in enumerate(parsed_data.questions):
        question_entity = QuestionBank(
            interview_id=interview_id,
            category=q.category,
            question_text=q.question_text,
            sort_order=i + 1
        )
        await question_repo.add(question_entity)
