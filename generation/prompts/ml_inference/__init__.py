# generation/prompts/ml_inference/__init__.py
"""
ML Inference Prompts
"""

from .model_serving_prompt import MODEL_SERVING_PROMPT
from .inference_optimization_prompt import INFERENCE_OPTIMIZATION_PROMPT
from .rag_prompt import RAG_PROMPT
from .vector_db_prompt import VECTOR_DB_PROMPT

ML_INFERENCE_PROMPTS = {
    "model_serving": MODEL_SERVING_PROMPT,
    "inference_optimization": INFERENCE_OPTIMIZATION_PROMPT,
    "rag": RAG_PROMPT,
    "vector_db": VECTOR_DB_PROMPT
}

__all__ = [
    "ML_INFERENCE_PROMPTS",
    "MODEL_SERVING_PROMPT",
    "INFERENCE_OPTIMIZATION_PROMPT",
    "RAG_PROMPT",
    "VECTOR_DB_PROMPT"
]