from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.turns.user_start.vad_user_turn_start_strategy import VADUserTurnStartStrategy
from pipecat.turns.user_start.transcription_user_turn_start_strategy import TranscriptionUserTurnStartStrategy
from pipecat.transports.websocket.server import (
    SingleClientWebsocketServerParams,
    SingleClientWebsocketServerTransport,
)
import asyncio
import time
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.frames.frames import Frame, EndFrame, CancelFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame, TTSSpeakFrame, BotStartedSpeakingFrame, BotStoppedSpeakingFrame

from src import config
from src.serializers import AudioFrameSerializer

class SilenceTimeoutProcessor(FrameProcessor):
    """
    Monitors candidate silence during a live interview session.

    Activation is gated behind notify_client_connected() — the silence checker
    does NOT start on StartFrame (pipeline boot). It only starts once the
    candidate's WebSocket client has actually connected, preventing the
    processor from firing spurious "Take your time." TTS frames before anyone
    is on the call.

    Warning flags (sent_5s, sent_10s, sent_20s) are reset only when the USER
    speaks — not when the bot speaks — so the bot's own TTS output cannot
    re-trigger a silence prompt immediately after finishing a turn.
    """
    def __init__(self, candidate_name: str, timeout_seconds: int = 30):
        super().__init__()
        self.candidate_name = candidate_name
        self.timeout_seconds = timeout_seconds
        self.last_speech_time = time.time()
        self._check_task = None
        self._active = False
        self._client_connected = False
        self.bot_speaking = False
        self.sent_5s = False
        self.sent_10s = False
        self.sent_20s = False

    def notify_client_connected(self):
        """
        Called by the bot's on_client_connected transport event handler.
        Resets the silence timer and spawns the background silence-checking
        coroutine for the first time. Must be called exactly once per session.
        """
        self._client_connected = True
        self._active = True
        self.last_speech_time = time.time()
        # Cancel any stale check task (safety guard) before creating a fresh one
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
        self._check_task = asyncio.create_task(self._check_silence())

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Do not activate on StartFrame — wait for the client to connect.
        # StartFrame fires when the Pipecat pipeline boots, which can be many
        # seconds before the browser WebSocket client actually connects.

        # Reset silence timer and warning flags only on USER speech activity.
        # Bot speech must NOT reset these flags — doing so caused the old
        # infinite "Take your time." loop where the bot would trigger its own
        # silence countdown reset after every TTS utterance.
        if isinstance(frame, (UserStartedSpeakingFrame, UserStoppedSpeakingFrame)):
            self.last_speech_time = time.time()
            self.sent_5s = False
            self.sent_10s = False
            self.sent_20s = False

        elif isinstance(frame, BotStartedSpeakingFrame):
            # Track bot-speaking state so _check_silence can pause its elapsed
            # calculation while the bot is actively speaking. We intentionally
            # do NOT reset sent_Xs flags here.
            self.bot_speaking = True

        elif isinstance(frame, BotStoppedSpeakingFrame):
            # Once the bot finishes its turn, reset the silence baseline so the
            # candidate gets a fresh window to respond — but do not clear flags.
            self.bot_speaking = False
            self.last_speech_time = time.time()

        elif isinstance(frame, (EndFrame, CancelFrame)):
            self._active = False
            if self._check_task and not self._check_task.done():
                self._check_task.cancel()

        # Always forward the frame downstream.
        await self.push_frame(frame, direction)

    async def _check_silence(self):
        """Background coroutine — only runs after notify_client_connected()."""
        while self._active:
            await asyncio.sleep(0.5)
            if not self._active:
                break

            # Pause elapsed calculation while the bot is speaking so its own
            # TTS output does not count as candidate silence.
            if self.bot_speaking:
                continue

            elapsed = time.time() - self.last_speech_time
            if elapsed >= 30:
                await self.push_frame(TTSSpeakFrame("It seems we've lost connection. I will end the interview now."))
                await asyncio.sleep(3)
                await self.push_frame(EndFrame())
                self._active = False
                break
            elif elapsed >= 20 and not self.sent_20s:
                self.sent_20s = True
                await self.push_frame(TTSSpeakFrame("Are you still there?"))
            elif elapsed >= 10 and not self.sent_10s:
                self.sent_10s = True
                await self.push_frame(TTSSpeakFrame("Would you like me to repeat the question?"))
            elif elapsed >= 5 and not self.sent_5s:
                self.sent_5s = True
                await self.push_frame(TTSSpeakFrame("Take your time."))

def create_transport() -> SingleClientWebsocketServerTransport:
    return SingleClientWebsocketServerTransport(
        params=SingleClientWebsocketServerParams(
            audio_out_enabled=True,
            audio_out_sample_rate=16000,
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            add_wav_header=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            serializer=AudioFrameSerializer(),
        ),
        host=config.WEBSOCKET_HOST,
        port=config.WEBSOCKET_PORT,
    )

def create_services():
    """Instantiates and returns the STT, LLM, and TTS service objects.

    Uses the settings= object pattern throughout, as the legacy keyword
    arguments (voice=, model=) were deprecated in pipecat-ai 1.4.0.
    """
    stt = DeepgramSTTService(
        api_key=config.DEEPGRAM_API_KEY,
        settings=DeepgramSTTService.Settings(
            language="en-US",
            model=config.STT_MODEL,
        ),
    )

    tts = DeepgramTTSService(
        api_key=config.DEEPGRAM_API_KEY,
        settings=DeepgramTTSService.Settings(
            voice=config.TTS_VOICE,
            sample_rate=16000,
        ),
    )

    llm = GroqLLMService(
        api_key=config.GROQ_API_KEY,
        settings=GroqLLMService.Settings(
            model=config.LLM_MODEL,
        ),
    )

    return stt, llm, tts

def create_context_aggregator(system_prompt: str):
    context = LLMContext(messages=[{"role": "system", "content": system_prompt}])
    # Enable interruptions per project specifications by configuring VADUserTurnStartStrategy
    user_turn_strategies = UserTurnStrategies(
        start=[
            VADUserTurnStartStrategy(enable_interruptions=True),
            TranscriptionUserTurnStartStrategy()
        ]
    )
    user_params = LLMUserAggregatorParams(
        user_turn_strategies=user_turn_strategies,
        user_turn_stop_timeout=1.5
    )
    context_aggregator = LLMContextAggregatorPair(context, user_params=user_params)
    return context_aggregator

def assemble_pipeline(
    transport, 
    stt, 
    llm, 
    tts, 
    context_aggregator, 
    user_persistence, 
    bot_persistence, 
    silence_processor
) -> Pipeline:
    return Pipeline([
        transport.input(),
        stt,
        user_persistence,               # Intercepts user transcription frames before consumption
        context_aggregator.user(),
        silence_processor,
        llm,
        tts,
        transport.output(),
        bot_persistence,                # Intercepts bot response frames and triggers db save on turn end
        context_aggregator.assistant(), # Updates context with assistant response chunks after they are spoken
    ])
