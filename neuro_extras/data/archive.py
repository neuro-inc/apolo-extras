"""Module for archive management operations (compression and extraction)"""
import abc
import logging
from pathlib import Path

from ..utils import CLIRunner
from .common import ArchiveType, Resource, ensure_folder_exists


logger = logging.getLogger(__name__)


class ArchiveManager(metaclass=abc.ABCMeta):
    """Interface for archive management"""

    @abc.abstractmethod
    async def compress(self, source: Resource, destination: Resource) -> Resource:
        """Compress source into destination"""
        raise NotImplementedError

    @abc.abstractmethod
    async def extract(self, source: Resource, destination: Resource) -> Resource:
        """Extract source into destination"""
        raise NotImplementedError


class TarManager(ArchiveManager, CLIRunner):
    """Utility class for handling tar archives"""

    async def compress(self, source: Resource, destination: Resource) -> Resource:
        """Compress source into destination using tar command"""
        command = "tar"
        if destination.archive_type == (~ArchiveType.TAR):
            raise ValueError(
                f"Can't compress into {destination.url} with TarManager: "
                f"unsupported archive type {destination.archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.TAR)}"
            )
        mapping = {
            ArchiveType.TAR_GZ: "zcf",
            ArchiveType.TAR_BZ: "jcf",
            ArchiveType.TAR_PLAIN: "cf",
        }
        subcommand = mapping[destination.archive_type]
        args = [
            subcommand,
            str(destination),
            f"--exclude={destination.filename}",
            str(source),
        ]
        await self.run_command(command=command, args=args)
        return destination

    async def extract(self, source: Resource, destination: Resource) -> Resource:
        """Extract source into destination using tar command"""
        command = "tar"
        if source.archive_type == (~ArchiveType.TAR):
            raise ValueError(
                f"Can't extract {source} with TarManager: "
                f"unsupported archive type {source.archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.TAR)}"
            )
        mapping = {
            ArchiveType.TAR_GZ: "zxvf",
            ArchiveType.TAR_BZ: "jxvf",
            ArchiveType.TAR_PLAIN: "xvf",
        }
        subcommand = mapping[source.archive_type]
        args = [subcommand, str(source), f"-C", str(destination)]
        destination.as_path().mkdir(exist_ok=True, parents=True)
        await self.run_command(command=command, args=args)
        return destination


class GzipManager(ArchiveManager, CLIRunner):
    """Utility class for handling gzip archives"""

    async def compress(self, source: Path, destination: Path) -> Path:
        """Compress source into destination using gzip command"""
        command = "gzip"
        archive_type = ArchiveType.get_type(destination)
        if archive_type == (~ArchiveType.GZ):
            raise ValueError(
                f"Can't compress into {destination} with GzipManager: "
                f"unsupported archive type {archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.GZ)}"
            )
        if source.is_dir():
            raise ValueError(
                "gzip does not support folder compression, "
                "use .tar.gz extension instead."
            )
        args = ["-rkvf", str(source)]
        await self.run_command(command=command, args=args)
        # gzip does not support setting destination
        temp_destination = str(source) + ".gz"
        # TODO: add support for non-unix OS
        await self.run_command("mv", [temp_destination, str(destination)])
        return destination

    async def extract(self, source: Path, destination: Path) -> Path:
        """Extract source into destination using gunzip command"""
        command = "gunzip"
        archive_type = ArchiveType.get_type(destination)
        if archive_type == (~ArchiveType.GZ):
            raise ValueError(
                f"Can't extract {destination} with GzipManager: "
                f"unsupported archive type {archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.GZ)}"
            )
        args = ["--keep", str(source)]
        await self.run_command(command=command, args=args)
        temp_destination = str(source.with_suffix(""))  # gzip extracts inplace
        await self.run_command("mv", [temp_destination, str(destination)])
        return destination


class ZipManager(ArchiveManager, CLIRunner):
    """Utility class for handling zip archives"""

    async def compress(self, source: Path, destination: Path) -> Path:
        """Compress source into destination using zip command"""
        command = "zip"
        archive_type = ArchiveType.get_type(destination)
        if archive_type == (~ArchiveType.ZIP):
            raise ValueError(
                f"Can't compress into {destination} with ZipManager: "
                f"unsupported archive type {archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.ZIP)}"
            )
        # check if works as expected
        args = ["-rv", str(destination), str(source)]
        await self.run_command(command=command, args=args)
        return destination

    async def extract(self, source: Path, destination: Path) -> Path:
        """Extract source into destination using unzip command"""
        command = "unzip"
        archive_type = ArchiveType.get_type(destination)
        if archive_type == (~ArchiveType.ZIP):
            raise ValueError(
                f"Can't extract {destination} with ZipManager: "
                f"unsupported archive type {archive_type.name}. "
                f"Supported types: "
                f"{ArchiveType.get_extensions_for_type(ArchiveType.ZIP)}"
            )
        args = [str(source), "-d", str(destination)]
        destination.mkdir(exist_ok=True, parents=True)
        await self.run_command(command=command, args=args)
        return destination


def _get_archive_manager(archive: Resource) -> ArchiveManager:
    """Resolve appropriate archive manager"""
    mapping = {
        ArchiveType.TAR: TarManager(),
        ArchiveType.GZ: GzipManager(),
        ArchiveType.ZIP: ZipManager(),
    }
    archive_type = ArchiveType.get_type(archive.as_path())
    if archive_type == ArchiveType.UNSUPPORTED:
        supported_extensions = list(ArchiveType.get_extension_mapping())
        raise ValueError(
            f"Unsupported archive type for file {archive}, "
            f"supported types are {supported_extensions}"
        )
    return next(manager for type, manager in mapping.items() if type == archive_type)


async def copy(source: Resource, destination: Resource) -> Resource:
    """Copy source into destination"""
    command = "cp"
    args = [str(source), str(destination)]
    runner = CLIRunner()
    await runner.run_command(command=command, args=args)
    return destination


async def compress(source: Resource, destination: Resource) -> Resource:
    """Compress source into destination while
    inferring arhive type from destination"""
    ensure_folder_exists(destination)
    if source.filename is not None and destination.filename is not None:
        both_archives = ArchiveType.UNSUPPORTED not in (
            source.archive_type,
            destination.archive_type,
        )
        same_type = source.archive_type == destination.archive_type
        if both_archives and same_type:
            logger.info(
                "Skipping compression step - "
                "source is already archive of the same type"
            )
            return await copy(source=source, destination=destination)

    manager_implementation = _get_archive_manager(destination)
    logger.debug(
        f"Compressing {source} into {destination} "
        f"with {manager_implementation.__class__.__name__}"
    )
    return await manager_implementation.compress(source=source, destination=destination)


async def extract(source: Resource, destination: Resource) -> Resource:
    """Extract source into destination while
    inferring arhive type from source"""
    ensure_folder_exists(destination)

    manager_implementation = _get_archive_manager(source)
    logger.debug(
        f"Extracting {source} into {destination} "
        f"with {manager_implementation.__class__.__name__}"
    )
    return await manager_implementation.extract(source=source, destination=destination)
