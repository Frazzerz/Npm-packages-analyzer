import sys
from multiprocessing import Lock
from pathlib import Path
from typing import Optional

# Lock to synchronize prints between processes
print_lock = Lock()

# Original reference to stdout
_original_stdout = sys.__stdout__

# Global log file
_log_file: Optional[object] = None

def setup_logging(log_path: Path):
    """Setup the logging system - open the log file"""
    global _log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _log_file = open(log_path, 'w', encoding='utf-8', buffering=1)  # line buffered

def close_logging():
    """Close the log file"""
    global _log_file
    if _log_file:
        _log_file.close()
        _log_file = None

def synchronized_print(*args, **kwargs):
    """
    Atomic and synchronized print that ALWAYS writes:
    - To the terminal (original stdout)
    - To the log file (if configured)

    Also works correctly in multiprocessing mode.
    """
    with print_lock:
        # Print to terminal
        print(*args, **kwargs, file=_original_stdout)
        _original_stdout.flush()
        
        # Print to log file if configured
        if _log_file and not _log_file.closed:
            print(*args, **kwargs, file=_log_file)
            _log_file.flush()