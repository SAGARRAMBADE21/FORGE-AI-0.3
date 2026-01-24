# generation/prompts/testing/__init__.py
"""
Testing Prompts
"""

from .contract_testing_prompt import CONTRACT_TESTING_PROMPT
from .e2e_testing_prompt import E2E_TESTING_PROMPT
from .integration_testing_prompt import INTEGRATION_TESTING_PROMPT
from .load_testing_prompt import LOAD_TESTING_PROMPT
from .tdd_bdd_prompt import TDD_BDD_PROMPT
from .unit_testing_prompt import UNIT_TESTING_PROMPT

TESTING_PROMPTS = {
    "unit_testing": UNIT_TESTING_PROMPT,
    "integration_testing": INTEGRATION_TESTING_PROMPT,
    "e2e_testing": E2E_TESTING_PROMPT,
    "contract_testing": CONTRACT_TESTING_PROMPT,
    "load_testing": LOAD_TESTING_PROMPT,
    "tdd_bdd": TDD_BDD_PROMPT,
}

__all__ = [
    "TESTING_PROMPTS",
    "UNIT_TESTING_PROMPT",
    "INTEGRATION_TESTING_PROMPT",
    "E2E_TESTING_PROMPT",
    "CONTRACT_TESTING_PROMPT",
    "LOAD_TESTING_PROMPT",
    "TDD_BDD_PROMPT",
]
