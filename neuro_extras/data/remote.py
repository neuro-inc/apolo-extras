"""Module for copying files by running neu.ro jobs"""
import logging
from dataclasses import dataclass
from typing import List, Mapping, Optional, Tuple

from neuro_sdk import Client, DiskVolume, RemoteImage, SecretFile, Volume
from yarl import URL

from ..common import EX_OK, NEURO_EXTRAS_IMAGE, _attach_job_stdout
from ..utils import get_default_preset, select_job_preset
from .common import (
    Copier,
    UrlType,
    get_filename_from_url,
    parse_resource_spec,
    strip_filename_from_url,
)


logger = logging.getLogger(__name__)


@dataclass
class RemoteJobConfig:
    """Arguments, passed to `neuro_sdk.Client.jobs.start()`"""

    image: RemoteImage
    command: str
    env: Optional[Mapping[str, str]]
    secret_env: Optional[Mapping[str, URL]]
    volumes: List[Volume]
    secret_files: List[SecretFile]
    disk_volumes: List[DiskVolume]
    preset_name: str
    life_span: Optional[float]
    pass_config: bool

    @staticmethod
    def create(
        source: str,
        destination: str,
        neuro_client: Client,
        compress: bool = False,
        extract: bool = False,
        volumes: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        preset: Optional[str] = None,
        life_span: Optional[float] = None,
    ) -> "RemoteJobConfig":
        """Create `RemoteJobConfig` for a neu.ro copy job.

        Copy job will copy data from `source` to `destination`"""
        image = neuro_client.parse.remote_image(NEURO_EXTRAS_IMAGE)

        (patched_source, patched_destination, data_mounts) = _map_into_volumes(
            source=source,
            destination=destination,
        )
        logger.debug(f"Patched {source} into {patched_source}")
        logger.debug(f"Patched {destination} into {patched_destination}")
        logger.debug(f"Created job mountpoints: {data_mounts}")
        command = _build_data_copy_command(
            source=patched_source,
            destination=patched_destination,
            extract=extract,
            compress=compress,
        )
        all_volumes = volumes + data_mounts if volumes else data_mounts
        env_parse_result = neuro_client.parse.envs(env if env else [])
        volume_parse_result = neuro_client.parse.volumes(all_volumes)
        preset_name = select_job_preset(
            preset=preset, client=neuro_client
        ) or get_default_preset(neuro_client)
        return RemoteJobConfig(
            image=image,
            command=command,
            env=env_parse_result.env,
            secret_env=env_parse_result.secret_env,
            volumes=list(volume_parse_result.volumes),
            disk_volumes=list(volume_parse_result.disk_volumes),
            secret_files=list(volume_parse_result.secret_files),
            preset_name=preset_name,
            life_span=life_span,
            pass_config=True,
        )


class RemoteCopier(Copier):
    """Copier, that creates a job on neu.ro platform.
    Can copy data between neu.ro storage: or disk: and cloud storage."""

    def __init__(
        self,
        source: str,
        destination: str,
        neuro_client: Client,
        compress: bool = False,
        extract: bool = False,
        volumes: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        preset: Optional[str] = None,
        life_span: Optional[float] = None,
    ) -> None:
        super().__init__(source, destination)
        self.neuro_client = neuro_client
        self.job_config = RemoteJobConfig.create(
            source=source,
            destination=destination,
            neuro_client=neuro_client,
            compress=compress,
            extract=extract,
            volumes=volumes,
            env=env,
            preset=preset,
            life_span=life_span,
        )

    def _ensure_can_execute(self) -> None:
        if not (
            self.source_type == UrlType.PLATFORM
            and self.destination_type == UrlType.CLOUD
            or self.source_type == UrlType.CLOUD
            and self.destination_type == UrlType.PLATFORM
        ):
            raise ValueError(
                f"Can only copy between {UrlType.PLATFORM} and {UrlType.CLOUD}"
            )

    async def perform_copy(self) -> str:
        logger.info(f"Starting job from config: {self.job_config}")
        job = await self.neuro_client.jobs.start(
            image=self.job_config.image,
            command=self.job_config.command,
            env=self.job_config.env,
            secret_env=self.job_config.secret_env,
            volumes=self.job_config.volumes,
            secret_files=self.job_config.secret_files,
            disk_volumes=self.job_config.disk_volumes,
            preset_name=self.job_config.preset_name,
            life_span=self.job_config.life_span,
            pass_config=True,
        )
        logger.info(f"Started job {job.id}")
        exit_code = await _attach_job_stdout(job, self.neuro_client, name="copy")
        if exit_code == EX_OK:
            logger.info("Copy job finished")
        else:
            raise RuntimeError(f"Copy job failed: error code {exit_code}")

        return self.destination


def _map_into_volumes(
    source: str,
    destination: str,
    source_storage_mount_prefix: str = "/var/storage/source",
    destination_storage_mount_prefix: str = "/var/storage/destination",
    source_disk_mount_prefix: str = "/var/disk/source",
    destination_disk_mount_prefix: str = "/var/disk/destination",
) -> Tuple[str, str, List[str]]:
    """Map urls for platform storage into volume mounts.

    Returns (patched_source: str, patched_destination: str, volumes: List[str]),
    where patched_source and patched_destination are mount points for
    source and destination if they belong to platform storage
    and the same urls otherwise.
    """
    new_source, source_mounts = _map_singe_url_into_volume(
        url=source,
        storage_mount_prefix=source_storage_mount_prefix,
        disk_mount_prefix=source_disk_mount_prefix,
    )

    new_destination, destination_mounts = _map_singe_url_into_volume(
        url=destination,
        storage_mount_prefix=destination_storage_mount_prefix,
        disk_mount_prefix=destination_disk_mount_prefix,
        mount_files=False,
    )

    return new_source, new_destination, source_mounts + destination_mounts


def _map_singe_url_into_volume(
    url: str,
    storage_mount_prefix: str,
    disk_mount_prefix: str,
    mount_files: bool = True,
    mount_mode: str = "rw",
) -> Tuple[str, List[str]]:
    """Map storage or disk url into volume specification string
    and patch such url into a local path inside a container.

    storage: urls are mounted into storage_mount_prefix.
        If the url points to a file and mount_files is True,
        it is directly mounted as-is; is mount_files is False,
        parent directory is mounted instead (useful for
        mounting destination, as empy volumes are mounted as directories).

    disk: urls are mounted into disk_mount_prefix.
        If the path on disk is provided, patch url into that
        subfolder of disk_mount prefix.

    Other urls are left as-is.
    """
    volumes = []
    url_type = UrlType.get_type(url)
    filename = get_filename_from_url(url)
    if url_type == UrlType.STORAGE:
        if filename:
            if mount_files:
                resource_url = url
                mountpoint = f"{storage_mount_prefix}/{filename}"
            else:
                resource_url = strip_filename_from_url(url=url)
                mountpoint = f"{storage_mount_prefix}/"
            new_url = f"{storage_mount_prefix}/{filename}"
        else:
            resource_url = url
            mountpoint = f"{storage_mount_prefix}/"
            new_url = mountpoint
        volumes.append(f"{resource_url}:{mountpoint}:{mount_mode}")
    elif url_type == UrlType.DISK:
        schema, disk_id, path_on_disk, mode = parse_resource_spec(url)
        logger.debug(
            f"Parsed disk url {url} into schema: {schema}, disk_id: {disk_id} "
            f"path_on_disk: {path_on_disk}, mode: {mode}"
        )
        resource_url = f"{schema}:{disk_id}"
        mountpoint = f"{disk_mount_prefix}/"
        new_url = f"{disk_mount_prefix}{path_on_disk}" if path_on_disk else mountpoint
        volumes.append(f"{resource_url}:{mountpoint}:{mount_mode}")
    else:
        new_url = url
    return new_url, volumes


def _build_data_copy_command(
    source: str, destination: str, extract: bool, compress: bool
) -> str:
    """Build a neuro-extras data cp command"""
    command_prefix = ["neuro-extras", "data", "cp"]
    args = [source, destination]
    flags = []
    if compress:
        flags.append("-c")
    if extract:
        flags.append("-x")
    full_command = command_prefix + flags + args
    return " ".join(full_command)
