import logging
from tool_logger_handler import ToolLoggerHandler, QueueNames
import time

logger = logging.getLogger("my_service")
logger.setLevel(logging.DEBUG)

handler = ToolLoggerHandler(
    queue=QueueNames.TOOLS,
    service_name="my_service"
)
logger.addHandler(handler)


def main():
    logger.info("Service started successfully")
    logger.error("Database connection failed")

    for i in range(100000):
        logger.debug(f"Processing item {i}")
        time.sleep(0.01)


if __name__ == "__main__":
    main()