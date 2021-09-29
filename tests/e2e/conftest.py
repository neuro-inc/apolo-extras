import logging
import os
import subprocess
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from typing import (
    AsyncIterator,
    Callable,
    ContextManager,
    Iterator,
    List,
    Optional,
    Union,
)

import neuro_sdk as neuro_api  # NOTE: don't use async test functions (issue #129)
import pytest
from _pytest.capture import CaptureFixture
from neuro_cli.asyncio_utils import run as run_async, setup_child_watcher
from neuro_cli.const import EX_OK
from neuro_cli.main import cli as neuro_main
from tenacity import retry, stop_after_attempt, stop_after_delay
from typing_extensions import Protocol

from neuro_extras import main as extras_main
from neuro_extras.common import NEURO_EXTRAS_IMAGE
from neuro_extras.config import _build_registy_auth
from neuro_extras.image_builder import KANIKO_AUTH_PREFIX


logger = logging.getLogger(__name__)


class CLIRunner(Protocol):
    def __call__(
        self, args: List[str], enable_retry: bool = False
    ) -> "CompletedProcess[str]":
        ...


TERM_WIDTH = 80
SEP_BEGIN = "=" * TERM_WIDTH
SEP_END = "-" * TERM_WIDTH
TESTED_ARCHIVE_TYPES = ["tar.gz", "tgz", "zip", "tar"]

setup_child_watcher()


@dataclass
class Secret:
    name: str
    value: str

    def __repr__(self) -> str:
        return f"Secret(name='{self.name}', value='HIDDEN!'"


def generate_random_secret(name_prefix: str = "secret") -> Secret:
    return Secret(
        name=f"{name_prefix}-{uuid.uuid4().hex[:8]}",
        value=str(uuid.uuid4()),
    )


@pytest.fixture
def temp_random_secret(cli_runner: CLIRunner) -> Iterator[Secret]:
    secret = generate_random_secret()
    try:
        yield secret
    finally:
        cli_runner(["neuro", "secret", "rm", secret.name])


def gen_random_file(location: Union[str, Path], name: Optional[str] = None) -> Path:
    location = Path(location)
    location.mkdir(parents=True, exist_ok=True)
    name = name or f"file-{uuid.uuid4().hex[:8]}.txt"
    file = location / name
    file.write_text(str(uuid.uuid4()))
    return file


@pytest.fixture(scope="session", autouse=True)
def print_neuro_extras_image() -> None:
    logger.warning(f"Using neuro-extras image: '{NEURO_EXTRAS_IMAGE}'")


async def _async_get_bare_client() -> neuro_api.Client:
    """Return uninitialized neuro client."""
    return await neuro_api.get()


@pytest.fixture
def _neuro_client() -> Iterator[neuro_api.Client]:
    # Note: because of issue #129 we can't use async methods of the client,
    # therefore this fixture is private
    client = run_async(_async_get_bare_client())
    try:
        yield run_async(client.__aenter__())
    finally:
        run_async(client.__aexit__())  # it doesn't use arguments


@pytest.fixture
def current_cluster(_neuro_client: neuro_api.Client) -> str:
    return _neuro_client.cluster_name


@pytest.fixture
def current_user(_neuro_client: neuro_api.Client) -> str:
    return _neuro_client.username


@pytest.fixture
def switch_cluster(
    _neuro_client: neuro_api.Client,
) -> Callable[[str], ContextManager[None]]:
    @contextmanager
    def _f(cluster: str) -> Iterator[None]:
        orig_cluster = _neuro_client.config.cluster_name
        try:
            logger.info(f"Temporary cluster switch: {orig_cluster} -> {cluster}")
            run_async(_neuro_client.config.switch_cluster(cluster))
            yield
        finally:
            logger.info(f"Switch back cluster: {cluster} -> {orig_cluster}")
            try:
                run_async(_neuro_client.config.switch_cluster(orig_cluster))
            except Exception as e:
                logger.error(
                    f"Could not switch back to cluster '{orig_cluster}': {e}. "
                    f"Please run manually: 'neuro config switch-cluster {orig_cluster}'"
                )

    return _f


@pytest.fixture
async def dockerhub_auth_secret() -> AsyncIterator[Secret]:
    async with neuro_api.get() as neuro_client:
        secret_name = f"{KANIKO_AUTH_PREFIX}_{uuid.uuid4().hex}"
        auth_data = _build_registy_auth(
            # Why not v2: https://github.com/GoogleContainerTools/kaniko/pull/1209
            registry_uri="https://index.docker.io/v1/",
            username=os.environ["DOCKER_CI_USERNAME"],
            password=os.environ["DOCKER_CI_TOKEN"],
        )
        secret = Secret(secret_name, auth_data)
        try:
            await neuro_client.secrets.add(secret_name, auth_data.encode())
            yield secret
        finally:
            await neuro_client.secrets.rm(secret_name)


@pytest.fixture
def project_dir() -> Iterator[Path]:
    with TemporaryDirectory() as cwd_str:
        old_cwd = Path.cwd()
        cwd = Path(cwd_str)
        os.chdir(cwd)
        try:
            yield cwd
        finally:
            os.chdir(old_cwd)


@pytest.fixture
@retry(stop=stop_after_attempt(5) | stop_after_delay(5 * 10))
def cli_runner_old(capfd: CaptureFixture[str], project_dir: Path) -> CLIRunner:
    def _run_cli(
        args: List[str], enable_retry: bool = False
    ) -> "CompletedProcess[str]":
        args = args.copy()
        cmd = args.pop(0)
        if cmd not in ("neuro", "neuro-extras"):
            pytest.fail(f"Illegal command: {cmd}")

        run_cmd = f"Run '{cmd} {' '.join(args)}'"
        logger.info(run_cmd)
        capfd.readouterr()

        main = extras_main
        if cmd == "neuro":
            args = [
                "--show-traceback",
                "--disable-pypi-version-check",
                "--color=no",
            ] + args
            main = neuro_main

        code = EX_OK
        try:
            main(args)
        except SystemExit as e:
            code = e.code
        out, err = capfd.readouterr()
        out, err = out.strip(), err.strip()
        if code != EX_OK and enable_retry:
            logger.info(f"Stderr:\n{SEP_BEGIN}\n{err}\n{SEP_END}\nStderr finished")
            logger.warning(f"Stderr:\n{SEP_BEGIN}\n{err}\n{SEP_END}\nStderr finished")
            raise RuntimeError(f"Got '{code}' for '{cmd}'")
        return CompletedProcess(
            args=[cmd] + args, returncode=code, stdout=out, stderr=err
        )

    return _run_cli


@pytest.fixture
@retry(stop=stop_after_attempt(5) | stop_after_delay(5 * 10))
def cli_runner(project_dir: Path) -> CLIRunner:
    def _run_cli(
        args: List[str], enable_retry: bool = False
    ) -> "CompletedProcess[str]":
        proc = subprocess.run(args, capture_output=True, check=enable_retry, text=True)
        if proc.returncode:
            logger.warning(f"Got '{proc.returncode}' for '{' '.join(args)}'")
        logger.warning(proc.stderr)
        logger.debug(proc.stdout)
        return proc

    return _run_cli
