import logging
import sys

logger = logging.getLogger("SystemLogger")

def setup_logger(log_file: str = None) -> logging.Logger:
    """
    Sets up a centralized logger.

    Args:
        log_file (str, optional): The file path to store the logs. If None, logs are not saved to a file.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create or get the logger
    global logger
    logger.setLevel(logging.INFO)  # Adjust log level as needed

    # Define a log format
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # Create and add a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # If a log_file is provided, create and add a file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to the root logger to avoid duplicate logs
    logger.propagate = False

    return logger


# Example usage:
if __name__ == "__main__":
    logger = setup_logger("system.log")
    logger.info("Logger is set up and ready to log events.")
    logger.debug("This is a debug message (useful for development).")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")