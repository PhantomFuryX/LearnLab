import logging
import sys

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # You can add FileHandler here if you want to log to a file
    ]
)

def get_logger(name: str = "LearnLab"):
    return logging.getLogger(name)
