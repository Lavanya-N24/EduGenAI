import uuid
import logging

def generate_job_id() -> str:
    """Generate a unique job ID for processing pipeline."""
    return uuid.uuid4().hex[:12]

def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance setup from root config."""
    return logging.getLogger(name)
