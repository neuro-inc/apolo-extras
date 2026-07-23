from unittest import mock

import apolo_sdk
import click
import pytest
from yarl import URL

from apolo_extras.common import APOLO_EXTRAS_IMAGE
from apolo_extras.data import COPY_JOB_LIFESPAN, _run_copy_container


async def test_run_copy_container(_apolo_client: apolo_sdk.Client) -> None:
    await _run_copy_container(
        _apolo_client,
        src_cluster="othercluster",
        src_uri_str="storage://othercluster/myorg/myproject/data",
        dst_uri_str="storage://mycluster/myorg/myproject/data",
    )

    job_start_mock: mock.AsyncMock = _apolo_client.jobs.start  # type: ignore
    job_start_mock.assert_awaited_once()
    kwargs = job_start_mock.await_args_list[0].kwargs
    assert str(kwargs["image"]) == APOLO_EXTRAS_IMAGE
    assert kwargs["preset_name"] == "cpu-small"
    assert kwargs["command"] == (
        "apolo --show-traceback cp --progress -r -u -T "
        "storage://othercluster/myorg/myproject/data /storage"
    )
    assert kwargs["env"] == {"APOLO_CLUSTER": "othercluster"}
    assert kwargs["volumes"] == [
        apolo_sdk.Volume(
            storage_uri=URL("storage://mycluster/myorg/myproject/data"),
            container_path="/storage",
            read_only=False,
        ),
    ]
    assert kwargs["pass_config"] is True
    assert kwargs["life_span"] == COPY_JOB_LIFESPAN


async def test_run_copy_container_failed_job(_apolo_client: apolo_sdk.Client) -> None:
    with mock.patch(
        "apolo_extras.data._attach_job_stdout",
        mock.AsyncMock(return_value=125),
    ):
        with pytest.raises(click.ClickException, match="Unable to copy storage"):
            await _run_copy_container(
                _apolo_client,
                src_cluster="othercluster",
                src_uri_str="storage://othercluster/myorg/myproject/data",
                dst_uri_str="storage://mycluster/myorg/myproject/data",
            )
