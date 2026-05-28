from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from apolo_extras.data.common import Resource
from apolo_extras.data.fs import LocalFSCopier


@pytest.mark.asyncio
async def test_local_fs_copier_uses_copy_for_directory_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_dir = tmp_path / "source tree"
    source_dir.mkdir()
    (source_dir / "real.txt").write_text("payload")
    symlink = source_dir / "linked.txt"
    symlink.symlink_to(source_dir / "real.txt")
    destination_dir = tmp_path / "destination tree"

    copier = LocalFSCopier(
        source=Resource.from_path(source_dir),
        destination=Resource.from_path(destination_dir),
    )
    run_command = AsyncMock(return_value=None)
    monkeypatch.setattr(copier, "run_command", run_command)

    await copier.perform_copy()

    run_command.assert_awaited_once()
    assert run_command.await_args is not None
    kwargs = run_command.await_args.kwargs
    assert kwargs["command"] == "rclone"
    assert kwargs["args"][0] == "copy"
    assert "--links" in kwargs["args"]
    assert kwargs["args"][-2:] == [
        str(source_dir),
        str(destination_dir),
    ]


@pytest.mark.asyncio
async def test_local_fs_copier_uses_copyto_for_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_file = tmp_path / "source file.txt"
    source_file.write_text("payload")
    destination_file = tmp_path / "destination file.txt"

    copier = LocalFSCopier(
        source=Resource.from_path(source_file),
        destination=Resource.from_path(destination_file),
    )
    run_command = AsyncMock(return_value=None)
    monkeypatch.setattr(copier, "run_command", run_command)

    await copier.perform_copy()

    run_command.assert_awaited_once()
    assert run_command.await_args is not None
    kwargs = run_command.await_args.kwargs
    assert kwargs["command"] == "rclone"
    assert kwargs["args"][0] == "copyto"
    assert "--links" in kwargs["args"]
    assert kwargs["args"][-2:] == [
        str(source_file),
        str(destination_file),
    ]
