from __future__ import annotations

import json
from pathlib import Path

import pytest

from expertwiki.concurrency import BundleLock, BundleLockedError, FileMutationBatch, recover_file_journals


def test_bundle_lock_refuses_a_second_live_writer(tmp_path: Path) -> None:
    with BundleLock(tmp_path, timeout=0.01):
        with pytest.raises(BundleLockedError):
            with BundleLock(tmp_path, timeout=0.01):
                pass


def test_file_mutation_batch_rolls_back_uncommitted_write(tmp_path: Path) -> None:
    target = tmp_path / "wiki" / "page.md"
    target.parent.mkdir(parents=True)
    target.write_text("before\n")

    with FileMutationBatch(tmp_path, "test") as batch:
        batch.write_text(target, "after\n")

    assert target.read_text() == "before\n"


def test_recover_file_journal_restores_pre_state(tmp_path: Path) -> None:
    target = tmp_path / "wiki" / "page.md"
    target.parent.mkdir(parents=True)
    target.write_text("partial\n")
    journal_dir = tmp_path / ".expertwiki" / "journal"
    journal_dir.mkdir(parents=True)
    journal = journal_dir / "pending.json"
    journal.write_text(
        json.dumps(
            {
                "entries": [
                    {"path": "wiki/page.md", "absent": False, "content": "before\n"}
                ]
            }
        )
    )

    recovered = recover_file_journals(tmp_path)

    assert recovered == ["pending.json"]
    assert target.read_text() == "before\n"
    assert not journal.exists()
