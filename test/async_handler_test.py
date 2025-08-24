import pytest
import logging
import json
import asyncio
from unittest.mock import patch, MagicMock

from tool_logger_handler.handler import AsyncToolLoggerHandler
from tool_logger_handler.misc import QueueNames


@pytest.fixture
def mock_aio_pika():
    """Fixture to mock aio_pika connection and channel."""
    with patch(
        "tool_logger_handler.handler.aio_pika.connect_robust"
    ) as mock_connect_cls:
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = asyncio.Future()
        mock_connection.channel.return_value.set_result(mock_channel)
        mock_connect_cls.return_value = asyncio.Future()
        mock_connect_cls.return_value.set_result(mock_connection)
        yield mock_connection, mock_channel


@pytest.fixture
def async_logger():
    """Fixture to create an async logger."""
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.DEBUG)
    handler = AsyncToolLoggerHandler(
        queue=QueueNames.LOGS, service_name="my_async_service"
    )
    logger.addHandler(handler)
    yield logger
    # Clean up handlers after test
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

# TODO: Implement async tests using pytest-asyncio or similar framework