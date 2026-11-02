"""The closing timestamp line is computed in code and survives DST changes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm import runner  # noqa: E402
from llm.providers.base import GenerationResult, Provider  # noqa: E402
from llm.timestamps import apply_closing_line, closing_line, format_pacific  # noqa: E402
from llm.validators import validate_output  # noqa: E402


def _summary(downloaded, processed):
    return json.dumps({"Last 1 Days": {"types": {}}, "downloaded_at": downloaded,
                       "source_update_times": {"data_processed_at": processed}})


def test_standard_time():
    # The live case that was wrong: 19:36Z on 2026-11-01 is 11:36 AM PST (the model wrote 12:36).
    assert format_pacific("2026-11-01T19:36:00Z") == "November 1, 2026 at 11:36 AM PST"


def test_daylight_time():
    assert format_pacific("2026-10-15T22:15:07Z") == "October 15, 2026 at 3:15 PM PDT"


def test_fall_back_day_uses_both_offsets():
    # DST ended 2026-11-01 at 2:00 AM PDT: 07:00Z was still PDT, 10:20Z is PST.
    line = closing_line(_summary("2026-11-01T10:20:00Z", "2026-11-01T07:00:18Z"))
    assert line == ("This data summary was updated at November 1, 2026 at 2:20 AM PST and is based on "
                    "data published by the City of Long Beach at November 1, 2026 at 12:00 AM PDT.")


def test_spring_forward_day():
    # DST starts 2027-03-14 at 2:00 AM PST -> 3:00 AM PDT.
    assert format_pacific("2027-03-14T09:30:00Z") == "March 14, 2027 at 1:30 AM PST"
    assert format_pacific("2027-03-14T10:30:00Z") == "March 14, 2027 at 3:30 AM PDT"


def test_missing_or_bad_values():
    assert format_pacific(None) == "an unrecorded time"
    assert format_pacific("not a date") == "an unrecorded time"
    assert "an unrecorded time" in closing_line("{}")


def test_model_line_is_replaced():
    model = ("Graffiti reports rose to 29 this week.\n\nPlease use the Go Long Beach app.\n\n"
             "This data summary was updated at 2026-11-01 12:36:00 PM PST and is based on data "
             "published by the City of Long Beach at 2026-11-01 12:00:24 PM PST.")
    line = closing_line(_summary("2026-11-01T19:36:00Z", "2026-11-01T19:00:24Z"))
    out = apply_closing_line(model, line)
    assert out.count("This data summary was updated at") == 1
    assert out.endswith(line)
    assert "12:36" not in out and "Please use the Go Long Beach app." in out


def test_text_without_model_line_gets_one():
    out = apply_closing_line("Body text.", "This data summary was updated at X and is based on data "
                                           "published by the City of Long Beach at Y.")
    assert out == ("Body text.\n\nThis data summary was updated at X and is based on data published "
                   "by the City of Long Beach at Y.")


class _FakeProvider(Provider):
    name = "fake"

    def generate(self, request):
        body = ("The City of Long Beach received 163 service requests in the past 24 hours. Dumped items led "
                "with 43 new reports and graffiti followed with 29. Residents are encouraged to use the Go Long "
                "Beach app to report issues.")
        return GenerationResult(text=body + "\n\nThis data summary was updated at 03:20 PDT and is based on "
                                "data published by the City of Long Beach at 00:00 PDT.",
                                provider_name="fake", model_name="fake-1")


def test_runner_writes_code_generated_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "get_providers", lambda: [_FakeProvider()])
    out = runner.run_inference("24hours", _summary("2026-11-01T10:20:00Z", "2026-11-01T07:00:18Z"))
    text = Path(out).read_text()
    validate_output(text)
    assert text.endswith("updated at November 1, 2026 at 2:20 AM PST and is based on data published by "
                         "the City of Long Beach at November 1, 2026 at 12:00 AM PDT.")
    assert "03:20" not in text
    archived = list((tmp_path / "data/archive").rglob("summary_24_hour_*.txt"))
    assert len(archived) == 1 and archived[0].read_text() == text
