"""Reusable in-process Piper neural voice adapter."""
from pathlib import Path
from threading import Lock
import wave

class PersistentPiperEngine:
    def __init__(self, model, speaker=None):
        model = Path(model)
        if not model.is_file() or not Path(str(model) + ".json").is_file():
            raise FileNotFoundError(f"Missing Piper model or configuration: {model}")
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(model))
        self.speaker = speaker
        self.lock = Lock()

    def synthesize(self, text, destination):
        if not text.strip():
            raise ValueError("Speech text cannot be empty")
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.lock, wave.open(str(output), "wb") as wav_file:
                kwargs = {} if self.speaker is None else {"speaker_id": self.speaker}
                self.voice.synthesize_wav(text, wav_file, **kwargs)
            with wave.open(str(output), "rb") as wav_file:
                if wav_file.getnframes() <= 0:
                    raise RuntimeError("Piper produced empty speech")
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output
