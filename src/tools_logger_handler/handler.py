"""A logging handler that sends log records to a RabbitMQ queue."""

from datetime import datetime
import json
import logging
import pika
import socket
import sys
import os

from .misc import QueueNames, LogEntryMessage


class ToolLoggerHandler(logging.Handler):
    """A logging handler that sends log records to a RabbitMQ queue."""

    def __init__(self, queue: QueueNames, service_name: str):
        """Initialize the ToolLoggerHandler.
        Args:
            queue (QueueNames): The name of the RabbitMQ queue to send logs to.
            service_name (str): The name of the service generating the logs.
        """
        super().__init__()

        self._host = os.getenv("RABBITMQ_HOST", "localhost")
        self._queue = queue
        self._service_name = service_name

        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self._host)
        )
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=self.queue.name, durable=True)

    @property
    def queue(self) -> QueueNames:
        """Get the current queue name.
        Returns:
            QueueNames: The current queue name.
        """
        return self._queue

    @queue.setter
    def queue(self, value: QueueNames):
        """Set the queue name and declare it in RabbitMQ.
        Args:
            value (QueueNames): The queue name to set.
        Raises:
            ValueError: If the value is not an instance of QueueNames Enum.
        """
        if not isinstance(value, QueueNames):
            raise ValueError("queue must be an instance of QueueNames Enum")
        self._queue = value
        self._channel.queue_declare(queue=self.queue.name, durable=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Send the log record to the RabbitMQ queue.

        Args:
            record (logging.LogRecord): The log record to be sent.

        Raises:
            Exception: If there is an error sending the log record.
        """
        try:
            if hasattr(record, "queue"):
                self.queue = record.queue

            log_entry = LogEntryMessage(
                service=self._service_name,
                level=record.levelname,
                message=record.getMessage(),
                time=datetime.fromtimestamp(record.created).isoformat(),
                host=socket.gethostname(),
            )
            self._channel.basic_publish(
                exchange="",
                routing_key=self.queue.name,
                body=json.dumps(log_entry.__dict__),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ),
            )
            print(f" [x] Sent log to {self.queue.name}: {log_entry}")
        except Exception as e:
            print(f"Failed to emit log record: {e}", file=sys.stderr)
