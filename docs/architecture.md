# Architecture Decisions

## ADR-001: Deterministic Parsing Over LLM Translation

**Status:** Accepted

**Context:**
Users want to describe image augmentations in natural language, but LLMs can hallucinate non-existent transforms.

**Decision:**
Use explicit string-matching parser instead of asking LLMs to "improve" prompts.

**Consequences:**

- ✅ Prevents hallucination of fake transforms
- ✅ Guarantees only real Albumentations transforms are used
- ✅ Provides deterministic, debuggable behavior
- ❌ May miss some valid interpretations of ambiguous language
- ❌ Requires maintaining mapping dictionaries
