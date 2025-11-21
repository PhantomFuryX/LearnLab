from dotenv import load_dotenv
import logging
import sys

# Load environment variables from .env file
load_dotenv()

# Configure root logger (if not already configured)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Generic import for logger
from .logger import get_logger
