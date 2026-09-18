#!/usr/bin/env python3
"""Interactive CLI testing application for DD House RAG Assistant.

Usage:
    cd ~/ddhs/DD_HOUSE_KKD/rag
    python3 test_rag.py
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 1. Environment & Path Configuration
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent if CURRENT_DIR.name == "rag" else CURRENT_DIR
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Load environment variables strictly from ../backend/.env
from dotenv import load_dotenv
BACKEND_ENV = ROOT_DIR / "backend" / ".env"
load_dotenv(BACKEND_ENV)

from rag.config import settings
from rag.pipeline.rag_pipeline import RAGPipeline


def check_vector_db() -> bool:
    """Validate that the vector database exists before running."""
    index_file = settings.VECTOR_DB_PATH / "index.pkl"
    if not index_file.exists():
        print("\n[ERROR] Vector database not found. Run the ingestion/indexing pipeline first.")
        print(f"Expected location: {index_file}\n")
        return False
    return True


def format_sources_brief(sources: list) -> str:
    """Format concise sources for inline response display."""
    if not sources:
        return ""
    lines = ["\nSources:"]
    for s in sources:
        cat = s.get("category", "")
        name = s.get("name", "")
        if cat:
            lines.append(f"- {cat}")
        if name:
            lines.append(f"- {name}")
        lines.append("- verified: true")
    return "\n".join(lines)


def verify_grok_auth() -> bool:
    """Safely verify Grok / LLM API authentication across key pool without printing secrets."""
    from rag.llm.key_manager import key_manager
    candidates = key_manager.get_candidate_slots()
    if not candidates:
        print("Grok API authentication: FAILED (No active API keys found in environment)")
        return False

    import httpx
    from openai import OpenAI

    for slot in candidates:
        key_val = slot.api_key
        base_url = settings._env_base_url or ("https://api.groq.com/openai/v1" if key_val.startswith("gsk_") else "https://api.x.ai/v1")
        model = settings._env_model or ("openai/gpt-oss-120b" if ("groq.com" in base_url or key_val.startswith("gsk_")) else "grok-4.6")

        try:
            client = OpenAI(
                api_key=key_val,
                base_url=base_url,
                http_client=httpx.Client(timeout=10.0)
            )
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly: GROK_TEST_OK"}],
                temperature=0.0
            )
            if res and res.choices and len(res.choices) > 0:
                print(f"Grok API authentication: SUCCESS (Active Key Slot: {slot.slot_id}, Total Keys: {key_manager.total_keys})")
                return True
        except Exception:
            continue

    print("Grok API authentication: FAILED (All configured keys failed initial ping)")
    return False


def print_debug_info(debug_data: Optional[Dict[str, Any]]):
    """Format and display debug retrieval and LLM prompt information as specified in Task 9."""
    if not debug_data or (not debug_data.get("original_query") and not debug_data.get("query")):
        print("\nNo previous query found to debug.\n")
        return

    orig_query = debug_data.get("original_query") or debug_data.get("query", "")
    norm_query = debug_data.get("normalized_query") or orig_query
    detected_intent = debug_data.get("detected_intent", "GENERAL")
    candidates = debug_data.get("candidates") or debug_data.get("results", [])
    accepted = debug_data.get("accepted", [])
    rejected = debug_data.get("rejected", [])
    verified_sent = debug_data.get("verified_sent", [])
    grounded = debug_data.get("grounded", False)
    confidence = debug_data.get("confidence", 0.0)
    llm_provider = debug_data.get("llm_provider", settings.LLM_PROVIDER)
    llm_model = debug_data.get("llm_model", settings.LLM_MODEL)
    llm_status = debug_data.get("llm_status", "SUCCESS")
    prompt = debug_data.get("prompt")

    print("\n## DEBUG\n")
    print("Original query:")
    print(orig_query)
    print("\nNormalized retrieval query:")
    print(norm_query)
    print("\nDetected retrieval intent:")
    print(detected_intent)
    print(f"\nCandidates retrieved: {len(candidates)}\n")

    for i, item in enumerate(candidates, 1):
        if len(item) == 3:
            chunk, score, reason = item
        else:
            chunk, score = item[:2]
            reason = "Semantic match"
        name = chunk.product or chunk.policy or "General Knowledge"
        verified_str = "true" if chunk.verified else "false"
        is_acc = chunk.verified and score >= settings.SIMILARITY_THRESHOLD
        acc_str = "true" if is_acc else "false"

        print(f"{i}. Category: {chunk.category}")
        print(f"   Name: {name}")
        print(f"   Score: {score:.2f}")
        print(f"   Verified: {verified_str}")
        print(f"   Intent/category relevance: {reason}")
        print(f"   Accepted: {acc_str}\n")

    print("Accepted Context:")
    if accepted:
        for item in accepted:
            chunk = item[0]
            name = chunk.product or chunk.policy or chunk.chunk_id
            print(f"- [{chunk.category}] {name}")
    else:
        print("- None")

    print("\nRejected Context:")
    if rejected:
        for item in rejected:
            chunk = item[0]
            score = item[1]
            name = chunk.product or chunk.policy or chunk.chunk_id
            if not chunk.verified:
                rej_reason = "Unverified knowledge status"
            else:
                rej_reason = f"Score {score:.2f} < threshold {settings.SIMILARITY_THRESHOLD}"
            print(f"- [{chunk.category}] {name} (Reason: {rej_reason})")
    else:
        print("- None")

    print(f"\nTotal accepted: {len(accepted)} documents")
    print(f"Total rejected: {len(rejected)} documents")
    print(f"Final context sent to LLM: {len(verified_sent)} documents\n")

    print("LLM Provider:")
    print("Grok" if "grok" in str(llm_provider).lower() else str(llm_provider).capitalize())
    print("\nModel:")
    print(llm_model)
    print("\nGeneration:")
    print(llm_status)
    print("\nGrounded:")
    print("true" if grounded else "false")
    print("\nConfidence:")
    print(f"{confidence:.2f}")

    if prompt and isinstance(prompt, dict):
        print("\n[PROMPT SENT TO LLM]")
        print("--- System Prompt ---")
        print(prompt.get("system", "")[:250] + "...")
        print("--- User Prompt ---")
        print(prompt.get("user", ""))

    print("-" * 50 + "\n")


def print_sources_info(debug_data: Optional[Dict[str, Any]]):
    """Display detailed sources from previous query."""
    if not debug_data or not debug_data.get("query"):
        print("\nNo previous query found to show sources for.\n")
        return

    query = debug_data.get("query", "")
    sources = debug_data.get("sources", [])
    results = debug_data.get("results", [])

    print("\nSOURCES")
    print("-" * 35)
    print(f"Query: {query}\n")

    if sources:
        for s in sources:
            cat = s.get("category", "product")
            name = s.get("name", "DD House Knowledge")
            stype = s.get("source_type", "type_1_verified")
            print(f"- Category   : {cat}")
            print(f"  Name       : {name}")
            print(f"  Type       : {stype}")
            print(f"  Verified   : true\n")
    elif results:
        for chunk, _ in results[:2]:
            name = chunk.product or chunk.policy or chunk.category
            print(f"- Category   : {chunk.category}")
            print(f"  Name       : {name}")
            print(f"  Type       : {chunk.source_type}")
            print(f"  Verified   : {'true' if chunk.verified else 'false'}\n")
    else:
        print("No verified sources matched this query.\n")
    print("-" * 35 + "\n")


def is_unknown_response(answer: str, grounded: bool) -> bool:
    """Determine if a response is an unknown / TBD / ungrounded fallback."""
    if not grounded:
        return True
    lower = answer.lower()
    unknown_indicators = [
        "don't have verified information",
        "do not have verified information",
        "no verified",
        "not available in the verified",
        "please contact dd house at 7013522727",
        "verified ingredient/allergen information for that product yet"
    ]
    return any(ind in lower for ind in unknown_indicators)


def run_test_suite(pipeline: RAGPipeline):
    """Run full test suite specified in Section 15 and report breakdown metrics."""
    TEST_CATEGORIES = {
        "BASIC": ["hi", "hello","namsate"],
        "BUSINESS": ["dd house", "what is dd house", "shop name", "address", "location", "timings", "contact"],
        "PRODUCT": ["cake", "chocolate", "choco", "brownie", "sauce", "lollipop"],
        "TYPO": ["caek", "cakk", "cke", "ckae", "choclate", "chocolatee", "choco", "chocoo", "browny", "brwine", "sause", "saucee"],
        "NATURAL_LANGUAGE": [
            "What cakes do you have?",
            "What chocolate items are available?",
            "Do you sell brownies?",
            "Where is your shop?",
            "What time do you close?",
            "Can I pick up my order?",
            "Do you provide delivery?"
        ],
        "UNKNOWN": [
            "explain",
            "quantum physics",
            "weather today",
            "who is the president",
            "random unrelated question"
        ]
    }

    print("\n" + "=" * 60)
    print("DD HOUSE RAG AUTOMATED TEST SUITE EXECUTION")
    print("=" * 60 + "\n")

    total_queries = 0
    successful_grounded = 0
    controlled_unknown = 0
    errors = 0
    typo_passed = 0
    typo_failed = 0

    for cat, queries in TEST_CATEGORIES.items():
        print(f"--- CATEGORY: {cat} ({len(queries)} queries) ---")
        for q in queries:
            total_queries += 1
            try:
                res = pipeline.query(q)
                ans = res.get("answer", "")
                grnd = res.get("grounded", False)
                dbg = pipeline.last_query_debug or {}
                intent = dbg.get("detected_intent", "GENERAL")

                is_unk = is_unknown_response(ans, grnd)
                if cat == "UNKNOWN":
                    if is_unk:
                        controlled_unknown += 1
                        status = "PASS (Safe fallback)"
                    else:
                        errors += 1
                        status = "FAIL (Hallucinated)"
                else:
                    if grnd and not is_unk:
                        successful_grounded += 1
                        status = "PASS (Grounded)"
                        if cat == "TYPO":
                            typo_passed += 1
                    elif cat == "BASIC" and grnd:
                        successful_grounded += 1
                        status = "PASS (Greeting)"
                    else:
                        errors += 1
                        status = "FAIL (Ungrounded/Unknown)"
                        if cat == "TYPO":
                            typo_failed += 1

                print(f"[{status:<20}] Q: {q:<36} | Intent: {intent}")
                print(f"   Ans: {ans.replace(chr(10), ' ')[:100]}...")

            except Exception as e:
                errors += 1
                if cat == "TYPO":
                    typo_failed += 1
                print(f"[ERROR               ] Q: {q:<36} | Error: {type(e).__name__}")
        print()

    print("=" * 60)
    print("TEST SUITE SUMMARY BREAKDOWN")
    print("=" * 60)
    print(f"Total queries:                 {total_queries}")
    print(f"Successful grounded responses: {successful_grounded}")
    print(f"Controlled unknown responses:  {controlled_unknown}")
    print(f"Errors:                        {errors}")
    print(f"Typo queries passed:           {typo_passed}")
    print(f"Typo queries failed:           {typo_failed}")
    print("=" * 60 + "\n")


def run_interactive_session(pipeline: RAGPipeline):
    """Run interactive terminal chatbot session."""
    print("=" * 50)
    print("DD HOUSE RAG TEST CHAT")
    print("=" * 50)
    print("\nRAG system initialized successfully.\n")
    print("Type your question.")
    print("Commands:")
    print("  exit / quit  -> stop")
    print("  sources      -> show sources for the previous answer")
    print("  debug        -> show retrieval/debug information for the previous query\n")
    print("=" * 50 + "\n")

    total_queries = 0
    successful_responses = 0
    unknown_tbd_responses = 0
    errors = 0

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            cmd_lower = user_input.lower()

            if cmd_lower in {"exit", "quit", "q"}:
                break

            if cmd_lower == "sources":
                print_sources_info(pipeline.last_query_debug)
                continue

            if cmd_lower == "debug":
                print_debug_info(pipeline.last_query_debug)
                continue

            # Process customer question through RAG pipeline
            total_queries += 1
            try:
                res = pipeline.query(user_input)
                answer = res.get("answer", "")
                grounded = res.get("grounded", False)
                sources = res.get("sources", [])

                print(f"\nBot: {answer}")
                
                # Optionally display concise sources if available
                if sources:
                    brief_src = format_sources_brief(sources)
                    if brief_src:
                        print(brief_src)
                print()

                if is_unknown_response(answer, grounded):
                    unknown_tbd_responses += 1
                else:
                    successful_responses += 1

            except Exception as e:
                errors += 1
                # Safely mask any internal secret in error messages
                err_msg = str(e)
                print(f"\n[Error processing query: {type(e).__name__}]\n")

        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

    # Print session summary upon exit
    print("\n" + "=" * 50)
    print("RAG TEST SUMMARY")
    print("=" * 50)
    print(f"\nTotal queries:\n{total_queries}\n")
    print(f"Successful responses:\n{successful_responses}\n")
    print(f"Unknown/TBD responses:\n{unknown_tbd_responses}\n")
    print(f"Errors:\n{errors}\n")
    print("=" * 50)
    print("TESTING COMPLETE")
    print("=" * 50 + "\n")


def main():
    # 1. Verify Vector Database
    if not check_vector_db():
        sys.exit(1)

    # 2. Check & verify API authentication (safe check without exposing secret)
    verify_grok_auth()

    # 3. Initialize Existing Pipeline
    try:
        pipeline = RAGPipeline()
    except Exception as e:
        print(f"[ERROR] Failed to initialize RAG pipeline: {type(e).__name__}")
        sys.exit(1)

    # 4. Handle CLI arguments if passed (e.g., single query or evaluation bench)
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in {"--test", "--suite", "-t"}:
            run_test_suite(pipeline)
            return
        elif arg in {"--bench", "-b"}:
            from rag.evaluation.evaluate import run_evaluation
            run_evaluation()
            return
        else:
            query = " ".join(sys.argv[1:])
            print(f"You: {query}")
            res = pipeline.query(query)
            print(f"Bot: {res['answer']}")
            if res.get("sources"):
                print(format_sources_brief(res["sources"]))
            return

    # 5. Run Interactive Session
    run_interactive_session(pipeline)


if __name__ == "__main__":
    main()
