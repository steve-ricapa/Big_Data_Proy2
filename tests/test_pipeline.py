import json

import pytest

from threat_intelligence import pipeline
from threat_intelligence.common.config import Settings
from threat_intelligence.incremental.state import State
from threat_intelligence.transformations.normalize import normalize


def test_failed_connection_recorded(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    source.write_text('{"vulnerabilities": []}')
    run = tmp_path / "run"
    pipeline.prepare(run, sources=[source])

    def fail(engine):
        raise ConnectionError("Deliberately unavailable")

    monkeypatch.setattr(pipeline, "connect", fail)
    with pytest.raises(ConnectionError):
        pipeline.load(run, "cassandra")
    assert pipeline.manifest(run)["stages"]["cassandra"]["status"] == "FAILED"


def test_partial_write_retry_does_not_advance_checkpoint(tmp_path, monkeypatch, cve):
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"vulnerabilities": [{"cve": cve}]}))
    run = tmp_path / "run"
    pipeline.prepare(run, sources=[source])
    pipeline.validate(run)
    monkeypatch.setattr(pipeline, "settings", lambda: Settings(state_dir=tmp_path))

    class Sink:
        fail = True

        def __init__(self):
            self.written = {}

        def initialize(self):
            pass

        def ping(self):
            pass

        def close(self):
            pass

        def count(self):
            return len(self.written)

        def write(self, rows, old):
            for row in rows:
                self.written[row["cve_id"]] = row
            if self.fail:
                raise ConnectionError("Partial write simulated")

    sink = Sink()
    monkeypatch.setattr(pipeline, "connect", lambda _: sink)
    with pytest.raises(ConnectionError):
        pipeline.load(run, "mongodb")
    state = State(tmp_path / "checkpoints.sqlite")
    assert state.previous("mongodb", normalize(cve)) is None
    state.close()
    sink.fail = False
    assert pipeline.load(run, "mongodb")["new"] == 1
    assert pipeline.load(run, "mongodb")["unchanged"] == 1
    assert sink.count() == 1
