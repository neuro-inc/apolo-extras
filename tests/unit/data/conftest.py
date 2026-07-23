import typing as t
from contextlib import ExitStack
from unittest import mock

import apolo_sdk
import pytest

from ..sdk_mocks import MockedApoloConfig


@pytest.fixture
async def _apolo_client() -> t.AsyncGenerator[apolo_sdk.Client, None]:
    with ExitStack() as stack:
        stack.enter_context(mock.patch("apolo_sdk.Config", MockedApoloConfig))
        stack.enter_context(mock.patch("apolo_sdk._client.Config", MockedApoloConfig))

        stack.enter_context(
            mock.patch("apolo_sdk._storage.Storage.mkdir", mock.AsyncMock())
        )
        stack.enter_context(
            mock.patch(
                "apolo_sdk._jobs.Jobs.start",
                mock.AsyncMock(return_value=mock.Mock(id="job-mocked-id")),
            )
        )
        stack.enter_context(
            mock.patch(
                "apolo_extras.data._attach_job_stdout",
                mock.AsyncMock(return_value=0),
            )
        )
        client = await apolo_sdk.get()
        try:
            yield await client.__aenter__()
        finally:
            await client.__aexit__()
