# Gemini AI Model Fallback Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Hacker News Daily Digest to use Gemini 3.8 Flash (`gemini-3.8-flash`) as the primary summarization model with Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`) as resilient fallback to fix AI summarization and translation failures.

**Architecture:** Model cascade updated in `src/summarizer.py` and defaults updated in `src/config.py`. When summarizing an article, the system attempts `gemini-3.8-flash`, automatically cascades to `gemini-3.5-flash-lite` if the primary model fails or is unavailable, and degrades to metadata if all models fail.

**Tech Stack:** Python 3.11+ / 3.14+, `requests`, `google-genai` REST API, `pytest`.

---

### Task 1: Update Config and Environment Defaults

**Files:**
- Modify: `src/config.py`
- Modify: `.env.example`
- Modify: `.github/workflows/daily_digest.yml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Update test_config.py for new default model**
- [ ] **Step 2: Run pytest to verify test_config fails on old default**
- [ ] **Step 3: Update src/config.py, .env.example, .github/workflows/daily_digest.yml to default to gemini-3.8-flash**
- [ ] **Step 4: Run pytest to verify test_config passes**
- [ ] **Step 5: Commit config changes**

---

### Task 2: Update Summarizer Model Cascade & Fallback Chain

**Files:**
- Modify: `src/summarizer.py`
- Test: `tests/test_summarizer.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: Update test_summarizer.py to test gemini-3.8-flash and fallback to gemini-3.5-flash-lite**
- [ ] **Step 2: Run pytest to verify tests fail on old model list**
- [ ] **Step 3: Update FALLBACK_MODELS and default preferred_model in src/summarizer.py**
- [ ] **Step 4: Run pytest across all test suites to verify 100% pass**
- [ ] **Step 5: Commit summarizer changes**

---

### Task 3: Update Bilingual Documentation

**Files:**
- Modify: `README.md`
- Modify: `README.vi.md`

- [ ] **Step 1: Update references in README.md and README.vi.md to reflect gemini-3.8-flash and gemini-3.5-flash-lite**
- [ ] **Step 2: Commit documentation changes**

