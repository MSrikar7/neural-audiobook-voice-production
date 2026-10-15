"""Unit tests for CLI Piper validation; no downloaded model required."""
from pathlib import Path
import pytest
from voice_production.neural import PiperEngine

def test_model_required(tmp_path):
    with pytest.raises(FileNotFoundError, match="model"):
        PiperEngine(tmp_path / "missing.onnx").synthesize("Hello", tmp_path / "test.wav")

def test_configuration_required(tmp_path):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"fixture")
    with pytest.raises(FileNotFoundError, match="configuration"):
        PiperEngine(model).synthesize("Hello", tmp_path / "test.wav")
