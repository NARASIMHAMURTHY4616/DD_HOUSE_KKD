"""Unit tests for LLM API Key Manager rotation, rate limiting, and failover behavior.
Tests all 8 mandatory scenarios defined in the requirements.
"""
import os
import time
import pytest
from unittest.mock import MagicMock, patch
from rag.llm.key_manager import LLMKeyManager, KeySlot
from rag.generation.generator import AnswerGenerator, is_rate_limit_error, is_auth_error
from rag.ingestion.chunker import DocumentChunk

class MockRateLimitError(Exception):
    def __init__(self, message="Rate limit reached"):
        super().__init__(message)
        self.status_code = 429

class MockAuthError(Exception):
    def __init__(self, message="Invalid API key"):
        super().__init__(message)
        self.status_code = 401

class MockBadRequestError(Exception):
    def __init__(self, message="Bad Request"):
        super().__init__(message)
        self.status_code = 400

@pytest.fixture
def dummy_chunks():
    return [
        DocumentChunk(
            chunk_id="chunk_test_1",
            text="Double Chocolate is a cake bowl sold by DD House for ₹89.",
            category="product",
            source_type="business_provided",
            verified=True,
            product="Double Chocolate"
        )
    ]

# ---------------------------------------------------------------------------
# Test 1: KEY_1 succeeds -> KEY_1 used
# ---------------------------------------------------------------------------
def test_scenario_1_single_key_success(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_key_1", "test_key_2"])

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="DD House offers Double Chocolate for ₹89."))]

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        client_instance.chat.completions.create.return_value = mock_resp
        mock_openai.return_value = client_instance

        ans, prompt, status, slot = generator._call_grok("What is the price of Double Chocolate?", dummy_chunks)
        assert status == "SUCCESS"
        assert slot == "KEY_1"
        assert "₹89" in ans
        # Ensure only 1 attempt was made
        assert client_instance.chat.completions.create.call_count == 1

# ---------------------------------------------------------------------------
# Test 2: KEY_1 returns 429 -> KEY_2 succeeds -> KEY_1 -> KEY_2 -> success
# ---------------------------------------------------------------------------
def test_scenario_2_failover_on_429(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_key_1", "test_key_2"])

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="DD House offers Double Chocolate for ₹89."))]

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        # First call raises 429, second call succeeds
        client_instance.chat.completions.create.side_effect = [
            MockRateLimitError("429 Too Many Requests"),
            mock_resp
        ]
        mock_openai.return_value = client_instance

        ans, prompt, status, slot = generator._call_grok("What is the price of Double Chocolate?", dummy_chunks)
        assert status == "SUCCESS"
        assert slot == "KEY_2"
        assert "₹89" in ans
        assert client_instance.chat.completions.create.call_count == 2
        # Verify KEY_1 was placed on cooldown
        assert km._slots[0].in_cooldown is True
        assert km._slots[1].in_cooldown is False

# ---------------------------------------------------------------------------
# Test 3: KEY_1 (429) -> KEY_2 (429) -> KEY_3 (succeeds)
# ---------------------------------------------------------------------------
def test_scenario_3_multi_key_failover_429(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_key_1", "test_key_2", "test_key_3"])

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="DD House offers Double Chocolate for ₹89."))]

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        client_instance.chat.completions.create.side_effect = [
            MockRateLimitError("429 Quota Exceeded"),
            MockRateLimitError("429 Rate Limit Exceeded"),
            mock_resp
        ]
        mock_openai.return_value = client_instance

        ans, prompt, status, slot = generator._call_grok("What is the price of Double Chocolate?", dummy_chunks)
        assert status == "SUCCESS"
        assert slot == "KEY_3"
        assert client_instance.chat.completions.create.call_count == 3
        # Verify slots 1 & 2 are in cooldown
        assert km._slots[0].in_cooldown is True
        assert km._slots[1].in_cooldown is True
        assert km._slots[2].in_cooldown is False

# ---------------------------------------------------------------------------
# Test 4: All keys return 429 -> Controlled LLM failure, No hallucination
# ---------------------------------------------------------------------------
def test_scenario_4_all_keys_rate_limited(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_key_1", "test_key_2"])

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        client_instance.chat.completions.create.side_effect = [
            MockRateLimitError("429 Too Many Requests"),
            MockRateLimitError("429 Too Many Requests")
        ]
        mock_openai.return_value = client_instance

        result = generator.generate("What is the price of Double Chocolate?", dummy_chunks, confidence=0.95)
        assert result["grounded"] is False
        assert result["llm_status"] == "RATE_LIMIT_EXHAUSTED"
        assert "temporarily unable to process that request" in result["answer"]

# ---------------------------------------------------------------------------
# Test 5: KEY_1 returns 400 -> do NOT rotate automatically
# ---------------------------------------------------------------------------
def test_scenario_5_bad_request_no_rotation(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_key_1", "test_key_2"])

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        client_instance.chat.completions.create.side_effect = MockBadRequestError("400 Bad Request: Invalid Parameter")
        mock_openai.return_value = client_instance

        # Should raise or gracefully fall back to grounded engine without rotating key
        with pytest.raises(MockBadRequestError):
            generator._call_grok("What is the price of Double Chocolate?", dummy_chunks)

        # Ensure KEY_1 was NOT marked rate limited or auth failed
        assert km._slots[0].in_cooldown is False
        assert km._slots[0].auth_failed is False
        # Ensure only 1 attempt was made (did not rotate to KEY_2)
        assert client_instance.chat.completions.create.call_count == 1

# ---------------------------------------------------------------------------
# Test 6: KEY_1 returns 401 -> KEY_2 succeeds -> KEY_1 marked unavailable -> KEY_2 success
# ---------------------------------------------------------------------------
def test_scenario_6_auth_failure_failover(dummy_chunks):
    km = LLMKeyManager(cooldown_seconds=60)
    km.set_keys(["test_invalid_key_1", "test_valid_key_2"])

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="DD House offers Double Chocolate for ₹89."))]

    generator = AnswerGenerator()

    with patch("openai.OpenAI") as mock_openai, patch("rag.generation.generator.key_manager", km):
        client_instance = MagicMock()
        client_instance.chat.completions.create.side_effect = [
            MockAuthError("401 Unauthorized: Invalid API Key"),
            mock_resp
        ]
        mock_openai.return_value = client_instance

        ans, prompt, status, slot = generator._call_grok("What is the price of Double Chocolate?", dummy_chunks)
        assert status == "SUCCESS"
        assert slot == "KEY_2"
        # KEY_1 must be permanently marked auth_failed
        assert km._slots[0].auth_failed is True
        assert km._slots[1].auth_failed is False

# ---------------------------------------------------------------------------
# Test 7: Only LLM_API_KEY exists -> existing single-key configuration continues working
# ---------------------------------------------------------------------------
def test_scenario_7_single_key_env_fallback():
    with patch.dict(os.environ, {"LLM_API_KEY": "single_fallback_key_xyz"}, clear=True):
        km = LLMKeyManager()
        assert km.total_keys == 1
        assert km._slots[0].slot_id == "KEY_1"
        assert km._slots[0].api_key == "single_fallback_key_xyz"
        assert km._slots[0].env_var == "LLM_API_KEY"

# ---------------------------------------------------------------------------
# Test 8: Some numbered keys are empty -> use KEY_1 and KEY_3
# ---------------------------------------------------------------------------
def test_scenario_8_gaps_in_numbered_keys():
    env_vars = {
        "LLM_API_KEY_1": "key_one_val",
        "LLM_API_KEY_2": "",
        "LLM_API_KEY_3": "key_three_val",
        "LLM_API_KEY_4": "   ",
        "LLM_API_KEY_5": "key_five_val"
    }
    with patch.dict(os.environ, env_vars, clear=True):
        km = LLMKeyManager()
        assert km.total_keys == 3
        slot_ids = [s.slot_id for s in km._slots]
        assert slot_ids == ["KEY_1", "KEY_3", "KEY_5"]
        assert km._slots[0].api_key == "key_one_val"
        assert km._slots[1].api_key == "key_three_val"
        assert km._slots[2].api_key == "key_five_val"
