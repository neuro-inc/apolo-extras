from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from apolo_extras.data.archive import copy
from apolo_extras.data.common import Resource
from apolo_extras.utils import CLIRunner


@pytest.mark.asyncio
async def test_archive_copy_uses_raw_local_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source tree" / "file name.txt"
    source.parent.mkdir()
    source.write_text("payload")
    destination = tmp_path / "destination tree" / "copied name.txt"

    run_command = AsyncMock(return_value=None)
    monkeypatch.setattr(CLIRunner, "run_command", run_command)

    await copy(Resource.from_path(source), Resource.from_path(destination))

    run_command.assert_awaited_once()
    assert run_command.await_args is not None
    kwargs = run_command.await_args.kwargs
    assert kwargs["command"] == "cp"
    assert kwargs["args"] == [str(source), str(destination)]
