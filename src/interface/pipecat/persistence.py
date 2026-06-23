from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import TranscriptionFrame, TextFrame, LLMFullResponseEndFrame, InterruptionFrame
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from src.infrastructure.db.database import AsyncSessionLocal
from src.infrastructure.db.repository import InterviewResponseRepository, InterviewRepository
from src.infrastructure.db.models import InterviewResponse

class TranscriptState:
    """Holds shared aggregation buffers between user and assistant pipelines."""
    def __init__(self, interview_id: UUID):
        self.interview_id = interview_id
        self.current_user_text = ""
        self.current_bot_text = ""


class UserTranscriptPersistenceProcessor(FrameProcessor):
    """Intercepts user transcription frames before they are consumed by the context aggregator."""
    def __init__(self, state: TranscriptState):
        super().__init__()
        self.state = state

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            self.state.current_user_text += f" {frame.text}"
        await self.push_frame(frame, direction)


class BotTranscriptPersistenceProcessor(FrameProcessor):
    """Intercepts LLM response text frames and saves the complete turn on LLM response end."""
    def __init__(self, state: TranscriptState):
        super().__init__()
        self.state = state

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            self.state.current_bot_text += frame.text
            
        elif isinstance(frame, (LLMFullResponseEndFrame, InterruptionFrame)):
            if self.state.current_bot_text.strip():
                await self._persist_turn()
                
        await self.push_frame(frame, direction)

    async def _persist_turn(self):
        user_msg = self.state.current_user_text.strip()
        bot_msg = self.state.current_bot_text.strip()
        
        async with AsyncSessionLocal() as session:
            interview_repo = InterviewRepository(session)
            response_repo = InterviewResponseRepository(session)
            
            interview = await interview_repo.get_by_id(self.state.interview_id)
            if not interview:
                return
                
            from src.infrastructure.db.models import QuestionBank
            from sqlalchemy.future import select
            
            q_stmt = select(QuestionBank).where(
                QuestionBank.interview_id == self.state.interview_id,
                QuestionBank.sort_order == interview.current_question_idx + 1
            )
            result = await session.execute(q_stmt)
            question = result.scalar_one_or_none()
            q_id = question.id if question else None
                
            turn = InterviewResponse(
                interview_id=self.state.interview_id,
                question_id=q_id,
                candidate_transcript=user_msg,
                bot_transcript=bot_msg
            )
            await response_repo.add(turn)
            
            interview.current_question_idx += 1
            await interview_repo.commit()
            
        # Reset buffers
        self.state.current_user_text = ""
        self.state.current_bot_text = ""

