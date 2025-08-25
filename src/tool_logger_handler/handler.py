"""A logging handler that sends log records to a RabbitMQ queue."""

import asyncio
import aio_pika
from datetime import datetime
from typing import Optional
import json
import logging
import pika
import socket
import sys
import os
from .misc import QueueNames, LogEntryMessage


class ToolLoggerHandlerBase(logging.Handler):
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

        self._connection: pika.BlockingConnection = None
        self._channel: pika.BlockingChannel = None

    def _get_log_entry(self, record: logging.LogRecord) -> LogEntryMessage:
        return LogEntryMessage(
            service=self._service_name,
            level=record.levelname,
            message=record.getMessage(),
            time=datetime.fromtimestamp(record.created).isoformat(),
            host=socket.gethostname(),
        )

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
        self._channel.queue_declare(queue=self.queue.value, durable=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Send the log record to the RabbitMQ queue.

        Args:
            record (logging.LogRecord): The log record to be sent.

        Raises:
            Exception: If there is an error sending the log record.
        """
        raise NotImplementedError("emit method must be implemented by subclasses")


class ToolLoggerHandler(ToolLoggerHandlerBase):
    """A logging handler that sends log records to a RabbitMQ queue."""

    def __init__(self, queue: QueueNames, service_name: str):
        """Initialize the ToolLoggerHandler.
        Args:
            queue (QueueNames): The name of the RabbitMQ queue to send logs to.
            service_name (str): The name of the service generating the logs.
        """
        super().__init__(queue, service_name)

        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self._host)
        )
        self._channel = self._connection.channel()
        self._channel.queue_declare(queue=self.queue.value, durable=True)

    def emit(self, record: logging.LogRecord) -> None:
        """Send the log record to the RabbitMQ queue.

        Args:
            record (logging.LogRecord): The log record to be sent.

        Raises:
            Exception: If there is an error sending the log record.
        """
        try:
            # check if the record has a 'queue' attribute to change the queue dynamically
            # for instance, logger.error("error message", extra={"queue": QueueNames.ALERTS})
            if hasattr(record, "queue"):
                self.queue = record.queue

            log_entry = self._get_log_entry(record)
            self._channel.basic_publish(
                exchange="",
                routing_key=self.queue.value,
                body=json.dumps(log_entry.__dict__),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                ),
            )
            print(f" [x] Sent log to {self.queue.value}: {log_entry}")
        except Exception as e:
            print(f"Failed to emit log record: {e}", file=sys.stderr)


class AsyncToolLoggerHandler(ToolLoggerHandlerBase):
    """An async version of ToolLoggerHandler using aio-pika."""

    def __init__(
        self,
        queue: QueueNames,
        service_name: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        super().__init__(queue, service_name)
        self._loop = loop or asyncio.get_event_loop()

        self._connection : Optional[aio_pika.RobustConnection] = None
        self._channel : Optional[aio_pika.RobustChannel] = None

        self._loop.create_task(self._connect())

    async def _connect(self):
        try:
            self._connection = await aio_pika.connect_robust(
                f"amqp://guest:guest@{self._host}/", loop=self._loop
            )
            self._channel = await self._connection.channel()
            await self._channel.declare_queue(self.queue.value, durable=True)
        except Exception as e:
            print(f"AsyncToolLoggerHandler failed to connect: {e}")

    async def _send(self, message: dict, queue_name: str):
        """Send a log message asynchronously to the specified queue."""
        if not self._channel:
            # Wait a bit and retry if channel is not ready
            await asyncio.sleep(0.1)
            if not self._channel:
                print("Channel not ready, dropping log message:", message)
                return
        
        if queue_name != self.queue.value:
            await self._channel.declare_queue(queue_name, durable=True)

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=queue_name,
        )

    def emit(self, record: logging.LogRecord) -> None:
        """Prepare the log record and schedule sending asynchronously."""
        log_entry = self._get_log_entry(record)

        # Determine target queue (default or overridden per record)
        target_queue = getattr(record, "queue", self.queue).value

        # Schedule sending asynchronously
        asyncio.ensure_future(
            self._send(log_entry.__dict__, target_queue), loop=self._loop
        )
        print(f" [x] Scheduled log to {target_queue}: {log_entry}")
