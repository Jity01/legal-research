# Optimization Implementation Summary

## Changes Made

### 1. **Increased Workers: 5 → 20** ✅
- Changed `max_workers` from 5 to 20
- Allows 20 parallel LLM API calls simultaneously
- **Speedup: ~4x**

### 2. **Increased Batch Size: 10 → 40** ✅
- Changed `cases_per_batch` from 10 to 40
- Processes 40 cases per LLM API call
- Reduces total API calls: 9,900 → 2,475 (for 99k cases)
- **Speedup: ~4x**

### 3. **Embedding-Based Prefiltering: 99k → 20k** ✅
- Added `_fast_embedding_prefilter()` method
- Uses OpenAI embeddings for query factors
- Tries to use stored embeddings from database first
- Falls back to generating embeddings on the fly if needed
- Keeps top 20,000 cases after embedding similarity
- **Speedup: ~5x** (reduces LLM calls from 9,900 to ~500)

### 4. **Parallel Processing** ✅
- Embedding generation uses parallel processing
- Text matching uses ThreadPoolExecutor
- Vector similarity calculations run in parallel

### 5. **Early Termination** ✅
- Stops processing chunks if enough high-quality results found
- Saves time when limit is specified

## Expected Performance

### Before Optimizations:
- **99,000 cases** ÷ 10 per batch = **9,900 LLM calls**
- With 5 workers: ~1,980 sequential batches
- Each call: ~3 seconds
- **Total: ~1.65 hours minimum** (realistically 4+ hours with overhead)

### After Optimizations:
1. **Embedding Prefilter**: 99k → 20k cases (1-2 minutes)
2. **20k cases** ÷ 40 per batch = **500 LLM calls**
3. With 20 workers: ~25 sequential batches
4. Each call: ~3 seconds
5. **Total LLM time: ~75 seconds = 1.25 minutes**
6. **Total time: ~3-4 minutes** ✅

## Implementation Details

### Embedding Prefilter Flow:
1. Generate embedding for query factors (cached)
2. For each 10k chunk of cases:
   - Try to fetch stored embeddings from `cases_factors.embedding` column
   - If stored embeddings exist: calculate cosine similarity directly
   - If not: generate embeddings for factors on the fly (batched)
   - Score all cases in chunk
3. Sort all scores, keep top 20k
4. Apply direction filter if needed

### LLM Processing Flow:
1. Process 20k prefiltered cases in chunks of 10k
2. Each chunk: fetch factors/holdings, then process with LLM
3. 40 cases per LLM batch, 20 parallel workers
4. Keep top results from each chunk
5. Merge and return final results

## Database Requirements

The code will work in two modes:

1. **If embeddings exist in database** (fastest):
   - Expects `cases_factors.embedding` column with vector embeddings
   - Can be JSON array or native vector type
   - Uses stored embeddings directly

2. **If embeddings don't exist** (still fast):
   - Generates embeddings on the fly using OpenAI
   - Batches factor texts to minimize API calls
   - Caches query embeddings

## Configuration

Current settings in `web/app.py`:
```python
similarity_matcher = SimilarityMatcher(
    max_workers=20,           # 20 parallel workers
    cases_per_batch=40,       # 40 cases per LLM call
    text_prefilter_size=20000, # Top 20k after embedding prefilter
)
```

## Testing

To verify the optimizations work:
1. Check logs for "Embedding prefilter" messages
2. Should see: "reduced 99,000 → 20,000 candidates"
3. Should see: "Processing 20,000 prefiltered cases in 2 chunks"
4. Should see: "Processing 500 LLM batches (20,000 total cases)"
5. Total time should be ~3-5 minutes instead of 4 hours
