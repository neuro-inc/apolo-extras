import logging

from ..conftest import run_cli

logger = logging.getLogger(__name__)


def _run_command(cmd: str, args: list[str]) -> tuple[int, str, str]:
    logger.info(f"Running: {[cmd] + args}")
    result = run_cli([cmd] + args)
    return result.returncode, result.stdout, result.stderr
