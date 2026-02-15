"""
FORGE Universal Edit Console

Interactive NLP-powered console for editing any FORGE-generated output
using natural language commands.
"""

__version__ = "0.1.0"

from .console import EditConsole
from .nlp_interpreter import NLPInterpreter, EditIntent
from .file_manager import FileManager, FileContext
from .diff_viewer import DiffViewer

__all__ = [
    "EditConsole",
    "NLPInterpreter",
    "EditIntent",
    "FileManager",
    "FileContext",
    "DiffViewer",
]
