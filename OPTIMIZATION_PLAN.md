# Search Performance Optimization Plan

## Current Bottlenecks (4 hours → 5 minutes = 48x speedup needed)

### 1. **LLM API Calls - MAJOR BOTTLENECK** ⚠️

- **Current**: Processing ALL 99k cases with LLM
- **Math**: 99,000 cases ÷ 10 per batch = 9,900 LLM calls
- **Time**: 9,900 calls × 3 seconds = 29,700 seconds = **8.25 hours**
- **With 5 workers**: Still ~1,980 sequential batches = **~1.1 hours minimum**

### 2. **No Pre-filtering with Text Similarity**

- Currently fetches ALL cases, then processes ALL with LLM
- Text similarity exists but isn't used to reduce candidate set

### 3. **Small Batch Size**

- Only 10 cases per LLM call
- Could process 20-30 cases per call

### 4. **Limited Parallelism**

- Only 5 workers
- Could use 15-20 workers (OpenAI allows high concurrency)

## Optimization Strategy

### **OPTIMIZATION 1: Two-Stage Filtering (BIGGEST WIN - 20-50x speedup)**

**Goal**: Reduce LLM calls from 9,900 to 200-500

1. **Stage 1: Fast Text Matching** (1-2 minutes)

   - Use `_calculate_similarity_text()` on ALL 99k cases
   - This is FAST (no API calls, just text comparison)
   - Get top 5,000-10,000 candidates based on text similarity
   - Process in chunks, keep top N per chunk

2. **Stage 2: LLM Refinement** (3-4 minutes)
   - Only run LLM on the top 5k-10k candidates
   - 5,000 cases ÷ 25 per batch = 200 LLM calls
   - 200 calls × 3s ÷ 15 workers = **~40 seconds**

**Total time**: ~2-3 minutes for text matching + ~1 minute for LLM = **~3-4 minutes**

### **OPTIMIZATION 2: Increase Batch Size** (2-3x speedup)

- Change from 10 cases/batch → 25-30 cases/batch
- Reduces API calls: 9,900 → 3,300-4,000 calls
- **Time saved**: ~3-4 hours

### **OPTIMIZATION 3: Increase Workers** (3-5x speedup)

- Change from 5 → 15-20 workers
- OpenAI allows high concurrency (check rate limits)
- **Time saved**: ~2-3 hours

### **OPTIMIZATION 4: Early Termination** (1.5-2x speedup)

- Stop processing chunks if we already have enough high-scoring results
- If we have 1000 results with score > 0.7, we can stop early
- **Time saved**: ~1-2 hours

### **OPTIMIZATION 5: Parallel Text Matching** (1.5x speedup)

- Process text matching in parallel across chunks
- Use ThreadPoolExecutor for text similarity calculations
- **Time saved**: ~30-60 minutes

## Implementation Priority

1. **CRITICAL**: Two-stage filtering (text → LLM) - **20-50x speedup**
2. **HIGH**: Increase batch size to 25-30 - **2-3x speedup**
3. **HIGH**: Increase workers to 15-20 - **3-5x speedup**
4. **MEDIUM**: Early termination - **1.5-2x speedup**
5. **MEDIUM**: Parallel text matching - **1.5x speedup**

## Expected Results

**Current**: 4 hours
**After Optimizations**:

- Two-stage: 99k → 5k cases = 20x reduction
- Batch size: 10 → 25 = 2.5x reduction
- Workers: 5 → 15 = 3x reduction
- **Combined**: 20 × 2.5 × 3 = **150x theoretical speedup**
- **Realistic**: Accounting for overhead = **~30-50x speedup**
- **Final time**: 4 hours ÷ 40 = **~6 minutes** ✅

## Code Changes Needed

1. Add `_fast_text_prefilter()` method that:

   - Processes all cases with text similarity
   - Returns top 5k-10k candidates
   - Runs in parallel chunks

2. Modify `find_similar_cases()` to:

   - First run text prefilter
   - Then run LLM only on top candidates

3. Increase default batch size and workers in `__init__`

4. Add early termination logic
