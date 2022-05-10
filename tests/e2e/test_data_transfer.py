import os
import uuid
from typing import Callable, ContextManager

import pytest

from .conftest import CLIRunner


@pytest.mark.serial
def test_data_transfer(
    cli_runner: CLIRunner,
    current_user: str,
    switch_cluster: Callable[[str], ContextManager[None]],
) -> None:
    # Note: data-transfer runs copying job on dst_cluster and
    # we pushed test image to src_cluster, so it should be a target cluster
    src_cluster = os.environ["NEURO_CLUSTER_SECONDARY"]
    dst_cluster = os.environ["NEURO_CLUSTER"]

    with switch_cluster(src_cluster):
        result = cli_runner(["neuro-extras", "init-aliases"])
        assert result.returncode == 0, result

        src_path = (
            f"storage://{src_cluster}/{current_user}/copy-src/{str(uuid.uuid4())}"
        )
        result = cli_runner(["neuro", "mkdir", "-p", src_path])
        assert result.returncode == 0, result

        dst_path = (
            f"storage://{dst_cluster}/{current_user}/copy-dst/{str(uuid.uuid4())}"
        )

        result = cli_runner(
            ["neuro", "data-transfer", src_path, dst_path],
            enable_retry=True,
        )
        assert result.returncode == 0, result

        del_result = cli_runner(["neuro", "rm", "-r", src_path], enable_retry=True)
        assert del_result.returncode == 0, result

    with switch_cluster(dst_cluster):
        result = cli_runner(["neuro", "ls", dst_path], enable_retry=True)
        assert result.returncode == 0, result

        del_result = cli_runner(["neuro", "rm", "-r", dst_path])
        assert del_result.returncode == 0, result
