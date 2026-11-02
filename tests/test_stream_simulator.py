import random

from stream_simulator import generate_log_payload, payload_stream


def test_generated_payload_matches_api_contract() -> None:
    payload = generate_log_payload(random.Random(7))

    assert payload["service"]
    assert payload["severity"] in {"INFO", "WARN", "ERROR", "FATAL"}
    assert payload["message"]
    assert set(payload["meta_payload"]) == {"environment", "region", "pid"}


def test_payload_stream_honors_count() -> None:
    payloads = list(payload_stream(random.Random(3), count=4))

    assert len(payloads) == 4
