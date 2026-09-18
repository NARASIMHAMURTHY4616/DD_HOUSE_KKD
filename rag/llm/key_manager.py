"""Thread-safe API Key Manager with automatic rotation, rate-limit cooldown,
and failover support for DD House RAG Assistant.
"""
import os
import re
import time
import threading
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class KeySlot:
    slot_id: str              # e.g., "KEY_1", "KEY_2"
    api_key: str              # the raw secret API key (never printed/logged)
    env_var: str              # e.g., "LLM_API_KEY_1"
    cooldown_until: float = 0.0
    auth_failed: bool = False
    rate_limit_count: int = 0
    success_count: int = 0

    @property
    def is_available(self) -> bool:
        if self.auth_failed:
            return False
        return time.time() >= self.cooldown_until

    @property
    def in_cooldown(self) -> bool:
        return not self.auth_failed and time.time() < self.cooldown_until


class LLMKeyManager:
    """Manages a pool of LLM API keys with round-robin selection,
    rate-limit cooldown tracking, and failover capabilities.
    """
    def __init__(self, cooldown_seconds: Optional[int] = None):
        self._lock = threading.Lock()
        self._slots: List[KeySlot] = []
        self._current_index: int = 0
        self.cooldown_seconds = cooldown_seconds or int(os.getenv("LLM_KEY_COOLDOWN_SECONDS", "60"))
        self._load_keys_from_env()

    def _load_keys_from_env(self):
        """Discover and load all numbered and fallback API keys from environment."""
        loaded_keys: Dict[str, Tuple[str, str]] = {}  # slot_id -> (api_key, env_var)

        # 1. Search for numbered keys: LLM_API_KEY_1..50 or LLM_API_KEY1..50
        # Check all environment variables matching the pattern
        numbered_pattern = re.compile(r"^(?:LLM_API_KEY_?|API_KEY_?)(\d+)$", re.IGNORECASE)
        numbered_entries: List[Tuple[int, str, str]] = []

        for k, v in os.environ.items():
            match = numbered_pattern.match(k)
            if match:
                num = int(match.group(1))
                val = v.strip().strip("\"'").strip()
                if val:  # ignore empty/missing keys
                    numbered_entries.append((num, k, val))

        # Sort numbered keys by integer index (1, 2, 3...)
        numbered_entries.sort(key=lambda x: x[0])

        for num, env_name, key_val in numbered_entries:
            slot_id = f"KEY_{num}"
            if slot_id not in loaded_keys:
                loaded_keys[slot_id] = (key_val, env_name)

        # 2. Fallback to single key if no numbered keys found
        if not loaded_keys:
            single_key_fallbacks = [
                "LLM_API_KEY",
                "API_KEY",
                "XAI_API_KEY",
                "GROK_API_KEY",
                "OPENAI_API_KEY"
            ]
            for var in single_key_fallbacks:
                val = os.getenv(var, "").strip().strip("\"'").strip()
                if val:
                    loaded_keys["KEY_1"] = (val, var)
                    break

        # Build KeySlot objects
        self._slots = [
            KeySlot(
                slot_id=slot_id,
                api_key=key_val,
                env_var=env_var
            )
            for slot_id, (key_val, env_var) in loaded_keys.items()
        ]

    def set_keys(self, keys: List[str]):
        """Explicitly configure keys (used primarily for unit testing)."""
        with self._lock:
            self._slots = [
                KeySlot(slot_id=f"KEY_{i+1}", api_key=k, env_var=f"TEST_KEY_{i+1}")
                for i, k in enumerate(keys) if k and k.strip()
            ]
            self._current_index = 0

    @property
    def total_keys(self) -> int:
        return len(self._slots)

    @property
    def available_keys_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._slots if s.is_available)

    def get_candidate_slots(self) -> List[KeySlot]:
        """Return all slots ordered starting from the current round-robin pointer,
        filtering only those currently available (or on earliest expiring cooldown if none available).
        """
        with self._lock:
            if not self._slots:
                return []

            n = len(self._slots)
            # Reorder starting from _current_index
            ordered = [self._slots[(self._current_index + i) % n] for i in range(n)]

            available = [s for s in ordered if s.is_available]
            if available:
                return available

            # If all are in cooldown but not permanently failed, return non-auth-failed slots
            non_failed = [s for s in ordered if not s.auth_failed]
            return non_failed

    def advance_pointer(self):
        """Advance round-robin pointer to distribute load across keys."""
        with self._lock:
            if self._slots:
                self._current_index = (self._current_index + 1) % len(self._slots)

    def mark_rate_limited(self, slot_id: str, custom_cooldown: Optional[int] = None):
        """Mark a slot as temporarily unavailable due to 429/quota."""
        cd = custom_cooldown or self.cooldown_seconds
        with self._lock:
            for s in self._slots:
                if s.slot_id == slot_id:
                    s.cooldown_until = time.time() + cd
                    s.rate_limit_count += 1
                    break

    def mark_auth_failed(self, slot_id: str):
        """Mark a slot as permanently unavailable due to 401 Unauthorized."""
        with self._lock:
            for s in self._slots:
                if s.slot_id == slot_id:
                    s.auth_failed = True
                    break

    def record_success(self, slot_id: str):
        """Record a successful generation using a slot."""
        with self._lock:
            for s in self._slots:
                if s.slot_id == slot_id:
                    s.success_count += 1
                    s.cooldown_until = 0.0
                    break

    def reset_status(self):
        """Reset all cooldowns and auth failure statuses (for testing/recovery)."""
        with self._lock:
            for s in self._slots:
                s.cooldown_until = 0.0
                s.auth_failed = False
                s.rate_limit_count = 0


# Global singleton key manager
key_manager = LLMKeyManager()
