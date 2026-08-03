from collections.abc import Iterator

import pytest
from apolo_sdk import Client, Preset


class MockApoloClient(Client):
    def __init__(self) -> None:
        self._presets: dict[str, Preset] = {}

    @property
    def presets(self) -> dict[str, Preset]:
        return self._presets


@pytest.fixture
def mock_client() -> Iterator[MockApoloClient]:
    yield MockApoloClient._create()
