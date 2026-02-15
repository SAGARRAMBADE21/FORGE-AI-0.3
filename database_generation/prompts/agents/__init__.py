"""Agent modules for database design."""
from .classifier import CLASSIFIER_AGENT_XML
from .architect import ARCHITECT_AGENT_XML
from .data_modeler import DATA_MODELER_AGENT_XML
from .optimizer import OPTIMIZER_AGENT_XML
from .sql_writer import SQL_WRITER_AGENT_XML
from .reviewer import REVIEWER_AGENT_XML
from .chat_assistant import CHAT_AGENT_XML

__all__ = [
    "CLASSIFIER_AGENT_XML",
    "ARCHITECT_AGENT_XML",
    "DATA_MODELER_AGENT_XML",
    "OPTIMIZER_AGENT_XML",
    "SQL_WRITER_AGENT_XML",
    "REVIEWER_AGENT_XML",
    "CHAT_AGENT_XML",
]