"""Persistent adapter tests using a test double, not actual Piper audio."""
from pathlib import Path
import sys
import types
import wave
import pytest
from voice_production.persistent_neural import PersistentPiperEngine

def test_load_once_for_multiple_jobs(tmp_path, monkeypatch):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"fixture")
    Path(str(model) + ".json").write_text("{}")
    counter = {"loads": 0, "syntheses": 0}
    class FakePiperVoice:
        @classmethod
        def load(cls, path):
            counter["loads"] += 1
            return cls()
        def synthesize_wav(self, text, wav_file, **kwargs):
            counter["syntheses"] += 1
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x01\x00" * 512)
    monkeypatch.setitem(sys.modules, "piper", types.SimpleNamespace(PiperVoice=FakePiperVoice))
    engine = PersistentPiperEngine(model)
    for i in range(3):
        output = engine.synthesize("Hello world", tmp_path / f"{i}.wav")
        with wave.open(str(output), "rb") as wav:
            assert wav.getnframes() == 512
    assert counter == {"loads": 1, "syntheses": 3}

def test_invalid_text(tmp_path, monkeypatch):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"fixture")
    Path(str(model) + ".json").write_text("{}")
    class FakePiperVoice:
        @classmethod
        def load(cls, path):
            return cls()
    monkeypatch.setitem(sys.modules, "piper", types.SimpleNamespace(PiperVoice=FakePiperVoice))
    engine = PersistentPiperEngine(model)
    with pytest.raises(ValueError):
        engine.synthesize(" ", tmp_path / "bad.wav")
