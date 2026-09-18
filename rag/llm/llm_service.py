"""LLM service adapter for backward compatibility.
"""
from rag.generation.generator import AnswerGenerator

def get_llm_generator() -> AnswerGenerator:
    return AnswerGenerator()
