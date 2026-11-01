"""Tests for build_archive_index.py, run on a throwaway archive tree."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_archive_index as bai  # noqa: E402


def _run(root: Path, stamp: str, downloaded=None, processed="2026-10-15T22:00:00Z", texts=("4_hour", "24_hour", "7_day", "30_day", "90_day"),
         text_offset_s=60, fallback=()):
    y, m = stamp[:4], stamp[5:7]
    d = root / "data/archive" / y / m
    d.mkdir(parents=True, exist_ok=True)
    data = {"Last 1 Days": {"types": {}}}
    if downloaded:
        data["downloaded_at"] = downloaded
        data["source_update_times"] = {"data_processed_at": processed}
    (d / f"summary_json_{stamp}.json").write_text(json.dumps(data))
    hh, mm, ss = map(int, stamp[11:].split("-"))
    secs = hh * 3600 + mm * 60 + ss + text_offset_s
    tstamp = f"{stamp[:10]}_{secs // 3600:02d}-{secs % 3600 // 60:02d}-{secs % 60:02d}"
    for label in texts:
        body = "[Note: fallback]\nold text" if label in fallback else "A summary."
        (d / f"summary_{label}_{tstamp}.txt").write_text(body)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _index(root, month):
    return json.loads((root / f"data/archive/index/{month}.json").read_text())["runs"]


def test_pairs_texts_and_uses_pacific_date(tree):
    # 02:08 UTC on Nov 1 is still Oct 31 in Long Beach.
    _run(tree, "2026-11-01_02-08-40", downloaded="2026-11-01T02:07:00Z")
    _run(tree, "2026-11-01_10-21-57", downloaded="2026-11-01T10:20:00Z")
    sys.argv = ["x", "--all"]
    assert bai.main() == 0
    oct_runs, nov_runs = _index(tree, "2026-10"), _index(tree, "2026-11")
    assert [r["id"] for r in oct_runs] == ["2026-11-01_02-08-40"]
    assert oct_runs[0]["date_la"] == "2026-10-31"
    assert oct_runs[0]["window_end"] == "2026-11-01T02:08:40Z"
    assert set(oct_runs[0]["texts"]) == {"4hours", "24hours", "7days", "30days", "90days"}
    assert nov_runs[0]["date_la"] == "2026-11-01"
    months = json.loads((tree / "data/archive/index/months.json").read_text())["months"]
    assert months == [{"month": "2026-10", "days": {"2026-10-31": 1}}, {"month": "2026-11", "days": {"2026-11-01": 1}}]


def test_texts_never_attach_to_the_wrong_run(tree):
    # A manual re-run 10 minutes later: each run keeps its own texts.
    _run(tree, "2026-10-15_19-00-00", downloaded="2026-10-15T18:59:00Z", text_offset_s=60)
    _run(tree, "2026-10-15_19-10-00", downloaded="2026-10-15T19:09:00Z", text_offset_s=60)
    sys.argv = ["x", "--all"]
    bai.main()
    a, b = _index(tree, "2026-10")
    assert a["texts"]["24hours"].endswith("2026-10-15_19-01-00.txt")
    assert b["texts"]["24hours"].endswith("2026-10-15_19-11-00.txt")


def test_early_snapshot_without_metadata_and_missing_texts(tree):
    _run(tree, "2025-10-16_16-16-00", downloaded=None, texts=())
    sys.argv = ["x", "--all"]
    bai.main()
    (r,) = _index(tree, "2025-10")
    assert r["downloaded_at_exact"] is False and r["data_processed_at"] is None and r["texts"] == {}


def test_fallback_summaries_are_flagged(tree):
    _run(tree, "2026-10-15_19-00-00", downloaded="2026-10-15T18:59:00Z", fallback=("7_day",))
    sys.argv = ["x", "--all"]
    bai.main()
    assert _index(tree, "2026-10")[0]["fallback"] == ["7days"]


def test_unchanged_index_is_not_rewritten(tree):
    _run(tree, "2026-10-15_19-00-00", downloaded="2026-10-15T18:59:00Z")
    sys.argv = ["x"]
    bai.main()
    f = tree / "data/archive/index/2026-10.json"
    before = f.stat().st_mtime_ns
    bai.main()
    assert f.stat().st_mtime_ns == before


def test_incremental_run_leaves_older_months_alone(tree):
    _run(tree, "2026-08-15_19-00-00", downloaded="2026-08-15T18:59:00Z")
    _run(tree, "2026-09-15_19-00-00", downloaded="2026-09-15T18:59:00Z")
    _run(tree, "2026-10-15_19-00-00", downloaded="2026-10-15T18:59:00Z")
    sys.argv = ["x", "--all"]
    bai.main()
    aug = (tree / "data/archive/index/2026-08.json").read_text()
    sys.argv = ["x"]
    bai.main()
    assert (tree / "data/archive/index/2026-08.json").read_text() == aug
    assert [m["month"] for m in json.loads((tree / "data/archive/index/months.json").read_text())["months"]] == ["2026-08", "2026-09", "2026-10"]


def test_first_run_backfills_everything(tree):
    _run(tree, "2026-06-15_19-00-00", downloaded="2026-06-15T18:59:00Z")
    _run(tree, "2026-10-15_19-00-00", downloaded="2026-10-15T18:59:00Z")
    sys.argv = ["x"]  # no --all, no index yet
    bai.main()
    assert (tree / "data/archive/index/2026-06.json").exists()
