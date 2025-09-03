# Design Philosophy: Why We Use a Parser Instead of LLM Translation

## The Hallucination Problem

We intentionally **do not** ask LLMs to translate user prompts into "better" augmentation language because:

- LLMs may invent transforms that don't exist in Albumentations
- LLMs may hallucinate parameters or values outside valid ranges
- LLMs may create plausible-sounding but incorrect transform combinations
- This could lead to silent failures or unexpected behavior

## Our Approach: Constrained Parsing

Instead, we:

1. Accept natural language directly from users
2. Use a deterministic parser with explicit mappings
3. Only allow transforms that actually exist
4. Provide clear error messages and suggestions when parsing fails

This ensures reliability and prevents the tool from "making up" image transformations.
