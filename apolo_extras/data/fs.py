"""Module for copying files on local filesystem"""

import os
from pathlib import Path

from ..utils import CLIRunner
from .common import Copier, DataUrlType, Resource


class LocalFSCopier(Copier, CLIRunner):
    """Copier implementation for local file system operations"""

    def _ensure_can_execute(self) -> None:
        if not (
            self.source.data_url_type == DataUrlType.LOCAL_FS
            and self.destination.data_url_type == DataUrlType.LOCAL_FS
        ):
            raise ValueError("Only local filesystem is supported")

    async def perform_copy(self) -> Resource:
        """Perform copy through running rclone and return the url to destinaton"""
        destination_path = self.destination.as_local_path()
        destination_parent_folder, _ = os.path.split(destination_path)
        Path(destination_parent_folder).mkdir(exist_ok=True, parents=True)
        command = "rclone"
        source_path = self.source.as_local_path()
        if source_path.is_dir():
            # Preserve symlinks when copying directory trees from mounted storage.
            args = [
                "copy",
                "--links",
                "--checkers=16",  # https://rclone.org/docs/#checkers-n , default is 8
                "--transfers=8",  # https://rclone.org/docs/#transfers-n , default is 4.
                "--verbose=1",  # default is 0, set 2 for debug
                str(self.source.as_local_path()),
                str(self.destination.as_local_path()),
            ]
        else:
            args = [
                "copyto",  # TODO: investigate usage of 'sync' for potential speedup.
                "--links",
                "--checkers=16",  # https://rclone.org/docs/#checkers-n , default is 8
                "--transfers=8",  # https://rclone.org/docs/#transfers-n , default is 4.
                "--verbose=1",  # default is 0, set 2 for debug
                str(self.source.as_local_path()),
                str(self.destination.as_local_path()),
            ]
        await self.run_command(command=command, args=args)
        return self.destination
