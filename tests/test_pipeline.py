"""Database and input-validation tests without external synthesis dependencies."""
import pytest
from voice_production.core import Pipeline

def test_job_submission_and_lookup(tmp_path):
    pipeline = Pipeline(tmp_path)
    jid = pipeline.enqueue("chapter1", "Once upon a time.")
    record = pipeline.get(jid)
    assert record["status"] == "pending"
    assert record["chapter"] == "chapter1"
    assert pipeline.get("missing") is None

def test_input_validation(tmp_path):
    pipeline = Pipeline(tmp_path)
    with pytest.raises(ValueError):
        pipeline.enqueue("chapter1", " ")
    with pytest.raises(ValueError):
        pipeline.enqueue("chapter1", "a" * 10001)

def test_chapter_cannot_assemble_pending_jobs(tmp_path):
    pipeline = Pipeline(tmp_path)
    pipeline.enqueue("chapter1", "This is not yet synthesized.")
    with pytest.raises(ValueError):
        pipeline.assemble_chapter("chapter1")
