import logging
import coloredlogs

def setup_logger(name: str = None, level: str = 'INFO') -> logging.Logger:
    """
    Set up and configure a logger with colored output.
    
    Args:
        name (str, optional): The name for the logger. If None, uses __name__.
        level (str, optional): The logging level. Default is 'INFO'.
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Configure colored logging
    coloredlogs.install(
        level=level,
        logger=logging.getLogger(),
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level_styles={
            'info': {'color': 'white'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'}
        }
    )
    
    # Get or create logger
    logger = logging.getLogger(name or __name__)
    
    return logger

# Create a default logger instance
LOGGER = setup_logger() 