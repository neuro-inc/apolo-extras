from pathlib import Path
from unittest import mock

import apolo_sdk
import pytest
from yarl import URL

from apolo_extras.image import _build_image
from apolo_extras.image_builder import ImageBuilder

KANIKO_IMAGE = "gcr.io/kaniko-project/executor:v1.20.0-debug"


async def test_image_builder__min_parameters(
    remote_image_builder: ImageBuilder,
) -> None:
    context = "/path/to/context"

    await _build_image(
        dockerfile_path=Path("path/to/Dockerfile"),
        context=context,
        image_uri_str="image:targetimage:latest",
        use_cache=True,
        build_args=(),
        volume=(),
        env=(),
        build_tags=(),
        force_overwrite=False,
    )

    expected_storage_build_root = URL(
        "storage://mycluster/NO_ORG/myproject/.builds/mocked-uuid-4"
    )
    storage_mkdir_mock: mock.AsyncMock = remote_image_builder._client.storage.mkdir  # type: ignore # noqa: E501
    storage_mkdir_mock.assert_awaited()
    storage_mkdir_mock.assert_awaited_once_with(
        expected_storage_build_root, parents=True
    )
    storage_create_mock: mock.AsyncMock = remote_image_builder._client.storage.create  # type: ignore # noqa: E501
    storage_create_mock.assert_awaited_once_with(
        expected_storage_build_root / ".docker.config.json",
        mock.ANY,
    )
    subproc_mock: mock.AsyncMock = remote_image_builder._execute_subprocess  # type: ignore # noqa: E501
    assert subproc_mock.await_count == 1
    upload_ctx_cmd = subproc_mock.await_args_list[0][0][0]
    assert upload_ctx_cmd == [
        "apolo",
        "--disable-pypi-version-check",
        "cp",
        "--recursive",
        Path(context).resolve().as_uri(),
        str(expected_storage_build_root / "context"),
    ]
    job_start_mock: mock.AsyncMock = remote_image_builder._client.jobs.start  # type: ignore # noqa: E501
    job_start_mock.assert_awaited_once()
    kwargs = job_start_mock.await_args.kwargs
    assert str(kwargs["image"]) == KANIKO_IMAGE
    assert kwargs["preset_name"] == "cpu-small"
    assert kwargs["entrypoint"] is None
    assert kwargs["env"] == {"container": "docker"}
    assert kwargs["secret_env"] == {}
    assert kwargs["volumes"] == [
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / ".docker.config.json",
            container_path="/kaniko/.docker/config.json",
            read_only=True,
        ),
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / "context",
            container_path="/kaniko_context",
            read_only=False,
        ),
    ]
    assert kwargs["secret_files"] == []
    assert kwargs["disk_volumes"] == []
    assert kwargs["tags"] == (
        "kaniko-builds-image:image://mycluster/NO_ORG/myproject/targetimage:latest",
    )
    assert kwargs["life_span"] == 4 * 60 * 60
    assert kwargs["schedule_timeout"] == 20 * 60
    assert kwargs["project_name"] == "myproject"
    assert kwargs["command"].split(" ") == [
        "--context=/kaniko_context",
        "--dockerfile=/kaniko_context/path/to/Dockerfile",
        "--destination=registry.mycluster.noexists/NO_ORG/myproject/targetimage:latest",
        "--cache=true",
        "--cache-repo=registry.mycluster.noexists/NO_ORG/myproject/layer-cache/cache",
        "--verbosity=info",
        "--image-fs-extract-retry=1",
        "--push-retry=3",
        "--use-new-run=true",
        "--snapshot-mode=redo",
    ]


async def test_image_builder__full_parameters(
    remote_image_builder: ImageBuilder,
) -> None:
    context = "/path/to/context"

    await _build_image(
        dockerfile_path=Path("path/to/Dockerfile"),
        context=context,
        image_uri_str="image:targetimage:latest",
        use_cache=True,
        build_args=("ARG1=ARGVAL1", "ARG2=ARGVAL2"),
        volume=(
            "storage:somevol:/mnt/vol1",
            "storage:/someproject2/somevol2:/mnt/vol2",
        ),
        env=("ENV1=VAL1", "ENV2=VAL2"),
        preset="custom-preset",
        build_tags=("tag1", "tag2"),
        project_name="myproject",
        extra_kaniko_args="--some-kaniko-arg1 --some-kaniko-arg2=arg2val",
        force_overwrite=False,
    )

    expected_storage_build_root = URL(
        "storage://mycluster/NO_ORG/myproject/.builds/mocked-uuid-4"
    )
    job_start_mock: mock.AsyncMock = remote_image_builder._client.jobs.start  # type: ignore # noqa: E501
    job_start_mock.assert_awaited_once()
    kwargs = job_start_mock.await_args.kwargs
    assert str(kwargs["image"]) == KANIKO_IMAGE
    assert kwargs["preset_name"] == "custom-preset"
    assert kwargs["entrypoint"] is None
    assert kwargs["env"] == {"ENV1": "VAL1", "ENV2": "VAL2", "container": "docker"}
    assert kwargs["secret_env"] == {}
    assert kwargs["volumes"] == [
        apolo_sdk.Volume(
            storage_uri=URL("storage://mycluster/NO_ORG/myproject/somevol"),
            container_path="/mnt/vol1",
            read_only=False,
        ),
        apolo_sdk.Volume(
            storage_uri=URL("storage://mycluster/NO_ORG/someproject2/somevol2"),
            container_path="/mnt/vol2",
            read_only=False,
        ),
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / ".docker.config.json",
            container_path="/kaniko/.docker/config.json",
            read_only=True,
        ),
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / "context",
            container_path="/kaniko_context",
            read_only=False,
        ),
    ]
    assert kwargs["tags"] == (
        "tag1",
        "tag2",
        "kaniko-builds-image:image://mycluster/NO_ORG/myproject/targetimage:latest",
    )
    assert kwargs["command"].split(" ") == [
        "--context=/kaniko_context",
        "--dockerfile=/kaniko_context/path/to/Dockerfile",
        "--destination=registry.mycluster.noexists/NO_ORG/myproject/targetimage:latest",
        "--cache=true",
        "--cache-repo=registry.mycluster.noexists/NO_ORG/myproject/layer-cache/cache",
        "--verbosity=info",
        "--image-fs-extract-retry=1",
        "--push-retry=3",
        "--use-new-run=true",
        "--snapshot-mode=redo",
        "--build-arg",
        "ARG1=ARGVAL1",
        "--build-arg",
        "ARG2=ARGVAL2",
        "--build-arg",
        "ENV1",
        "--build-arg",
        "ENV2",
        "--some-kaniko-arg1",
        "--some-kaniko-arg2=arg2val",
    ]


async def test_image_builder__conflicting_kaniko_args(
    remote_image_builder: ImageBuilder,
) -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Extra kaniko arguments {'--image-fs-extract-retry'} overlap "
            "with autogenerated arguments. Please remove them "
            "in order to proceed or contact the support team."
        ),
    ):
        await _build_image(
            dockerfile_path=Path("path/to/Dockerfile"),
            context="/path/to/context",
            image_uri_str="image:targetimage:latest",
            use_cache=True,
            build_args=(),
            volume=(),
            env=(),
            preset=None,
            build_tags=(),
            project_name="myproject",
            extra_kaniko_args="--image-fs-extract-retry=3",
            force_overwrite=False,
        )


async def test_image_builder__custom_project(
    remote_image_builder: ImageBuilder,
) -> None:
    context = "/path/to/context"
    await _build_image(
        dockerfile_path=Path("path/to/Dockerfile"),
        context=context,
        image_uri_str="image:targetimage:latest",
        use_cache=True,
        build_args=(),
        volume=(),
        env=(),
        build_tags=(),
        force_overwrite=False,
        project_name="otherproject",
    )

    expected_storage_build_root = URL(
        "storage://mycluster/NO_ORG/otherproject/.builds/mocked-uuid-4"
    )
    storage_mkdir_mock: mock.AsyncMock = remote_image_builder._client.storage.mkdir  # type: ignore # noqa: E501
    storage_mkdir_mock.assert_awaited_once_with(
        expected_storage_build_root, parents=True
    )
    job_start_mock: mock.AsyncMock = remote_image_builder._client.jobs.start  # type: ignore # noqa: E501
    job_start_mock.assert_awaited_once()
    kwargs = job_start_mock.await_args.kwargs
    assert kwargs["project_name"] == "otherproject"
    assert kwargs["tags"] == (
        "kaniko-builds-image:image://mycluster/NO_ORG/otherproject/targetimage:latest",
    )
    assert kwargs["volumes"] == [
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / ".docker.config.json",
            container_path="/kaniko/.docker/config.json",
            read_only=True,
        ),
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / "context",
            container_path="/kaniko_context",
            read_only=False,
        ),
    ]
    assert kwargs["command"].split(" ") == [
        "--context=/kaniko_context",
        "--dockerfile=/kaniko_context/path/to/Dockerfile",
        "--destination=registry.mycluster.noexists/NO_ORG/otherproject/targetimage:latest",  # noqa: E501
        "--cache=true",
        "--cache-repo=registry.mycluster.noexists/NO_ORG/otherproject/layer-cache/cache",  # noqa: E501
        "--verbosity=info",
        "--image-fs-extract-retry=1",
        "--push-retry=3",
        "--use-new-run=true",
        "--snapshot-mode=redo",
    ]


async def test_image_builder__storage_context(
    remote_image_builder: ImageBuilder,
) -> None:
    context_uri_str = "storage:context"
    await _build_image(
        dockerfile_path=Path("path/to/Dockerfile"),
        context=context_uri_str,
        image_uri_str="image:targetimage:latest",
        use_cache=True,
        build_args=(),
        volume=(),
        env=(),
        build_tags=(),
        force_overwrite=False,
    )

    expected_storage_build_root = URL(
        "storage://mycluster/NO_ORG/myproject/.builds/mocked-uuid-4"
    )
    subproc_mock: mock.AsyncMock = remote_image_builder._execute_subprocess  # type: ignore # noqa: E501
    assert subproc_mock.await_count == 0
    job_start_mock: mock.AsyncMock = remote_image_builder._client.jobs.start  # type: ignore # noqa: E501
    job_start_mock.assert_awaited_once()
    kwargs = job_start_mock.await_args.kwargs
    assert kwargs["volumes"] == [
        apolo_sdk.Volume(
            storage_uri=expected_storage_build_root / ".docker.config.json",
            container_path="/kaniko/.docker/config.json",
            read_only=True,
        ),
        apolo_sdk.Volume(
            storage_uri=URL("storage://mycluster/NO_ORG/myproject/context"),
            container_path="/kaniko_context",
            read_only=False,
        ),
    ]
    assert kwargs["command"].split(" ") == [
        "--context=/kaniko_context",
        "--dockerfile=/kaniko_context/path/to/Dockerfile",
        "--destination=registry.mycluster.noexists/NO_ORG/myproject/targetimage:latest",
        "--cache=true",
        "--cache-repo=registry.mycluster.noexists/NO_ORG/myproject/layer-cache/cache",
        "--verbosity=info",
        "--image-fs-extract-retry=1",
        "--push-retry=3",
        "--use-new-run=true",
        "--snapshot-mode=redo",
    ]
