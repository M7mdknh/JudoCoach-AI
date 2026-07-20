from pathlib import Path

import pytest

from app.ingest import build_index


def test_storage_exists():
    assert Path("storage").exists()


def test_build_index_creates_persistent_storage(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    data_dir.mkdir()
    (data_dir / "sample.md").write_text(
        "Judo is a modern martial art and combat sport.",
        encoding="utf-8",
    )

    from app.config import config

    monkeypatch.setattr(config, "data_dir", str(data_dir))
    monkeypatch.setattr(config, "storage_dir", str(storage_dir))

    build_index()

    assert (storage_dir / "docstore.json").exists()
    assert (storage_dir / "index_store.json").exists()


def test_build_index_fails_on_empty_directory(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    data_dir.mkdir()

    from app.config import config

    monkeypatch.setattr(config, "data_dir", str(data_dir))
    monkeypatch.setattr(config, "storage_dir", str(storage_dir))

    with pytest.raises(RuntimeError, match="No documents found"):
        build_index()
