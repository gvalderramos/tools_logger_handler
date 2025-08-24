import logging
import pytest
import json
from unittest.mock import patch, MagicMock

from tools_logger_handler.handler import ToolLoggerHandler
from tools_logger_handler.misc import QueueNames, LogEntryMessage


@pytest.fixture
def mock_pika():
    """Fixture to mock pika connection and channel."""
    with patch("tools_logger_handler.handler.pika.BlockingConnection") as mock_conn_cls:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_conn_cls.return_value = mock_conn
        yield mock_conn, mock_channel


@pytest.fixture
def logger():
    """Fixture to create a logger."""
    logger = logging.getLogger(__file__)
    logger.setLevel(logging.DEBUG)
    handler = ToolLoggerHandler(queue=QueueNames.LOGS, service_name="my_service")
    logger.addHandler(handler)
    yield logger
    # Clean up handlers after test
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)


def test_emit_log_record(mock_pika, logger):
    mock_conn, mock_channel = mock_pika
    logger.info("hello world")

    # Check if queue was declared
    mock_channel.queue_declare.assert_any_call(queue=QueueNames.LOGS.name, durable=True)

    # Check that publish was called with expected message
    args = mock_channel.basic_publish.call_args
    if not args:
        pytest.fail("basic_publish was not called")
    kwargs = args[1]
    assert kwargs["routing_key"] == QueueNames.LOGS.name
    body = json.loads(kwargs["body"])
    assert body["service"] == "my_service"
    assert body["message"] == "hello world"
    assert body["level"] == "INFO"


def test_change_queue(mock_pika, logger):
    mock_conn, mock_channel = mock_pika
    logger.error("error message", extra={"queue": QueueNames.ALERTS})

    # Check if queue was changed and declared
    mock_channel.queue_declare.assert_any_call(
        queue=QueueNames.ALERTS.name, durable=True
    )

    # Check that publish was called with expected message
    args = mock_channel.basic_publish.call_args
    if not args:
        pytest.fail("basic_publish was not called")
    kwargs = args[1]
    assert kwargs["routing_key"] == QueueNames.ALERTS.name
    body = json.loads(kwargs["body"])
    assert body["service"] == "my_service"
    assert body["message"] == "error message"
    assert body["level"] == "ERROR"
