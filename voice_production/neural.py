"""Piper command-line adapter; loads a new process per synthesis."""
from dataclasses import dataclass
from pathlib import Path
import subprocess

@dataclass(frozen=True)
class PiperEngine:
    model: Path
    executable: str = "piper"
    speaker: int | None = None
    timeout_seconds: int = 300

    def synthesize(self, text, destination):
        model = Path(self.model)
        if not model.is_file():
            raise FileNotFoundError(f"Piper ONNX model not found: {model}")
        if not Path(str(model) + ".json").is_file():
            raise FileNotFoundError(f"Piper voice configuration missing: {model}.json")
        if not text.strip():
            raise ValueError("Speech text cannot be empty")
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [self.executable, "--model", str(model), "--output_file", str(output)]
        if self.speaker is not None:
            command.extend(["--speaker", str(self.speaker)])
        try:
            subprocess.run(command, input=text, text=True, capture_output=True,
                           check=True, timeout=self.timeout_seconds, encoding="utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            output.unlink(missing_ok=True)
            raise
        if not output.is_file() or output.stat().st_size < 44:
            raise RuntimeError("Piper did not produce a usable WAV file")
        return output
