# Tools Logger Handler

A custom Python logging handler that sends log records to a **RabbitMQ queue**.  
This library makes it easy to centralize tool health, status, and error logs using RabbitMQ, so they can later be collected, standardized, and visualized (e.g., with Prometheus + Grafana). It supports JSON structured messages with service name, log level, message, timestamp, and hostname. You can override the target queue per log call, and all messages are sent to durable queues with persistent delivery.

## Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/gvalderramos/tools_logger_handler.git
cd tools-logger-handler
pip install -e .
```

## Usage

### Basic Example

```python
import logging
from tools_logger_handler import ToolLoggerHandler, QueueNames, AsyncLoggerHandler

logger = logging.getLogger("my_service")
logger.setLevel(logging.INFO)

handler = ToolLoggerHandler(
    queue=QueueNames.LOGS,
    service_name="my_service"
)
logger.addHandler(handler)

logger.info("Service started successfully")
logger.error("Database connection failed")


# or

logger = logging.getLogger("my_service")
logger.setLevel(logging.INFO)

handler = AsyncLoggerHandler(
    queue=QueueNames.LOGS,
    service_name="my_service"
)
logger.addHandler(handler)

# that now will log threading safe
logger.info("Service started successfully")
logger.error("Database connection failed")
```

### Send to a Different Queue

You can override the target queue per log call using `extra`:

```python
logger.warning(
    "High memory usage detected",
    extra={"queue": QueueNames.ALERTS}
)
```

## Running Tests

This project uses `pytest`. The `pika` library is mocked in tests so RabbitMQ is not required.

```bash
pytest
```

If you use a `src/` layout, make sure `pytest` can find your package by adding a `pytest.ini`:

```ini
[pytest]
pythonpath = src
```

## Project Structure

```
your-project/
├─ src/
│  └─ tools_logger_handler/
│     ├─ __init__.py
│     ├─ handler.py        # RabbitMQ logging handler
│     └─ misc.py           # Supporting enums/classes (QueueNames, LogEntryMessage)
├─ tests/
│  └─ test_handler.py      # Unit tests with pika mocked
├─ examples/
│  └─ log_system.py        # Small example how to send logs to RabbitMQ system
├─ pyproject.toml
├─ pytest.ini
└─ README.md
```

## Configuration

- RabbitMQ host is taken from environment variable `RABBITMQ_HOST` (default: `localhost`).
- Queues are declared durable, and messages are published with `delivery_mode=2` (persistent).

## Architecture

```
      ┌────────────┐
      │   Your     │
      │   Tool     │
      └─────┬──────┘
            │ logs
            ▼
      ┌────────────┐
      │ RabbitMQ   │
      │ (queues)   │
      └─────┬──────┘
            │ messages
            ▼
      ┌────────────┐
      │ Collector  │
      │ Service    │
      └─────┬──────┘
            │ metrics
            ▼
┌─────────────────────┐
│ Prometheus / InfluxDB│
└─────────┬───────────┘
          │ scraped metrics
          ▼
       ┌────────┐
       │ Grafana │
       └────────┘
```

The handler sits at the **producer side**: your tool logs normally with Python’s `logging`, and the handler publishes structured log records to RabbitMQ. The collector service reads messages, normalizes them, and pushes metrics to a time-series database, which Grafana can visualize.

## RabbitMQ and Listener

The queue and services are available on this repository:
https://github.com/gvalderramos/tools_monitoring

## Roadmap

- [X] Create an async log handler using aio_pika
- [x] Provide Docker Compose for local development with RabbitMQ
- [ ] Add metrics exporter for Prometheus integration

## License

MIT License – feel free to use and modify.

