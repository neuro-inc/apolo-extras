import asyncio

import pytest

from apolo_extras.data import _run_copy_container
from apolo_extras.data.remote import _build_data_copy_command


def test_build_data_copy_command_quotes_spaces() -> None:
    command = _build_data_copy_command(
        source="storage://cluster/org/project/log_DateTime_2025-05-21 13:22:16",
        destination="/tmp/destination folder",
        extract=False,
        compress=False,
    )

    assert command.startswith("apolo-extras -v data cp ")
    assert "'storage://cluster/org/project/log_DateTime_2025-05-21 13:22:16'" in command
    assert "'/tmp/destination folder'" in command


@pytest.mark.asyncio
async def test_run_copy_container_quotes_shell_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    class DummyProcess:
        async def wait(self) -> int:
            return 0

    async def fake_create_subprocess_shell(cmd: str) -> DummyProcess:
        captured["cmd"] = cmd
        return DummyProcess()

    monkeypatch.setattr(
        asyncio, "create_subprocess_shell", fake_create_subprocess_shell
    )

    await _run_copy_container(
        src_cluster="imdc",
        src_uri_str="storage://imdc/amv/amv-cv/log_DateTime_2025-05-21 13:22:16",
        dst_uri_str="storage://apolo-main/amv/amv-cv/output folder",
    )

    assert "APOLO_CLUSTER=imdc" in captured["cmd"]
    assert (
        "'storage://imdc/amv/amv-cv/log_DateTime_2025-05-21 13:22:16'"
        in captured["cmd"]
    )
    assert (
        "'storage://apolo-main/amv/amv-cv/output folder:/storage:rw'" in captured["cmd"]
    )
    assert "'apolo --show-traceback cp --progress -r -u -T" in captured["cmd"]
