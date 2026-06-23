import json
from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    TTSAudioRawFrame,
    TextFrame,
    LLMTextFrame,
    TTSTextFrame,
    TranscriptionFrame,
    InterruptionFrame,
)

class AudioFrameSerializer(FrameSerializer):
    def __init__(self):
        super().__init__()

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, (OutputAudioRawFrame, TTSAudioRawFrame)):
            return frame.audio
        elif isinstance(frame, (TextFrame, LLMTextFrame, TTSTextFrame)):
            return json.dumps({"text": frame.text})
        elif isinstance(frame, InterruptionFrame):
            return json.dumps({"type": "interrupt"})
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, bytes):
            # The client sends raw 16kHz PCM audio bytes
            return InputAudioRawFrame(audio=data, sample_rate=16000, num_channels=1)
        elif isinstance(data, str):
            try:
                msg = json.loads(data)
                text = msg.get("text", "")
            except Exception:
                text = data
            return TranscriptionFrame(text=text, user_id="user", timestamp="", finalized=True)
        return None
