# Operational Guide (Phase 3)

This document provides operational guidance for the Phase 3 retrieval system.

**Last Updated:** January 2026

---

## Retention Considerations

### Embeddings Storage

Embeddings can grow significantly in size:

| Metric | Estimate |
|--------|----------|
| Vector dimension | 768 (nomic-embed-text) |
| Floats per vector | 768 × 8 bytes = ~6KB |
| JSON overhead | ~2x = ~12KB per embedding |
| 1000 chunks | ~12MB |
| 100,000 chunks | ~1.2GB |

**Recommendations:**

1. Monitor embedding table size:
   ```sql
   SELECT 
       OBJECT_NAME(p.object_id) AS table_name,
       SUM(a.total_pages) * 8 / 1024.0 AS size_mb
   FROM sys.partitions p
   JOIN sys.allocation_units a ON p.partition_id = a.container_id
   WHERE OBJECT_NAME(p.object_id) IN ('chunk', 'embedding')
   GROUP BY p.object_id;
   ```

2. Consider archiving old embeddings when:
   - Re-indexing with a new model
   - Updating chunking policy
   - Removing deprecated sources

3. Retention policy (suggested):
   - Keep embeddings as long as chunks are referenced
   - Archive retrieval logs after 90 days
   - Maintain at least one embedding per chunk for the active model

### Retrieval Logs

Retrieval logs grow with each query:

```sql
-- Count retrieval queries
SELECT COUNT(*) FROM llm.retrieval;

-- Queries per day
SELECT 
    CAST(created_utc AS DATE) AS query_date,
    COUNT(*) AS query_count
FROM llm.retrieval
GROUP BY CAST(created_utc AS DATE)
ORDER BY query_date DESC;
```

**Cleanup (optional):**

```sql
-- Archive old retrieval logs (> 90 days)
DELETE FROM llm.retrieval_hit
WHERE retrieval_id IN (
    SELECT retrieval_id FROM llm.retrieval
    WHERE created_utc < DATEADD(day, -90, GETUTCDATE())
);

DELETE FROM llm.retrieval
WHERE created_utc < DATEADD(day, -90, GETUTCDATE());
```

---

## Concurrency Controls

### Embedding Concurrency

Control concurrent embedding calls to Ollama:

```bash
# Limit to 1 concurrent call (default)
INDEX_EMBED_CONCURRENCY=1 python -m src.llm.retrieval.indexer ...

# Allow 2 concurrent calls
INDEX_EMBED_CONCURRENCY=2 python -m src.llm.retrieval.indexer ...
```

**Note:** Higher concurrency may overwhelm Ollama, especially without GPU.

### Indexing Best Practices

1. **Run indexing during low-traffic periods**
2. **Start with small manifests** to verify configuration
3. **Use incremental mode** for updates
4. **Monitor Ollama memory usage** during large indexing runs

---

## Troubleshooting

### Ollama Connection Issues

**Symptom:** `Failed to connect to Ollama` error

**Solutions:**

1. Verify Ollama container is running:
   ```bash
   docker compose ps ollama
   docker compose logs ollama
   ```

2. Check network connectivity:
   ```bash
   docker compose exec app curl http://ollama:11434/api/tags
   ```

3. Verify model is available:
   ```bash
   docker compose exec ollama ollama list
   ```

4. Pull the model if missing:
   ```bash
   docker compose exec ollama ollama pull nomic-embed-text
   ```

### Embedding Errors

**Symptom:** `Ollama embed API error` or empty embeddings

**Solutions:**

1. Check model supports embeddings (not all models do)
2. Verify input text is not too long:
   ```python
   # Check chunk sizes
   max_len = max(len(c) for c in chunks)
   print(f"Max chunk length: {max_len}")
   ```

3. Check Ollama logs for OOM errors:
   ```bash
   docker compose logs ollama | grep -i "error\|oom"
   ```

4. Reduce batch size if needed

### Slow Indexing

**Symptom:** Indexing takes very long

**Solutions:**

1. Check Ollama performance:
   ```bash
   # Time a single embedding
   time curl -X POST http://localhost:11434/api/embed \
       -d '{"model":"nomic-embed-text","input":"test"}'
   ```

2. GPU not available? Check Ollama is using GPU:
   ```bash
   docker compose logs ollama | grep -i "gpu\|cuda"
   ```

3. Reduce chunk count:
   - Increase `chunk_size`
   - Reduce sources in manifest

### Missing Embeddings

**Symptom:** Some chunks have no embeddings

**Solutions:**

1. Check for embedding failures:
   ```sql
   SELECT c.chunk_id, c.source_type
   FROM llm.chunk c
   LEFT JOIN llm.embedding e ON c.chunk_id = e.chunk_id
   WHERE e.embedding_id IS NULL;
   ```

2. Re-run indexer for failed sources

3. Check indexer output for errors

### Database Performance

**Symptom:** Slow retrieval queries

**Solutions:**

1. Verify indexes exist:
   ```sql
   SELECT name, type_desc
   FROM sys.indexes
   WHERE object_id = OBJECT_ID('llm.embedding');
   ```

2. Update statistics:
   ```sql
   UPDATE STATISTICS llm.chunk;
   UPDATE STATISTICS llm.embedding;
   ```

3. Consider partitioning for very large tables

---

## Monitoring

### Key Metrics

Monitor these metrics for healthy operation:

| Metric | Query |
|--------|-------|
| Total chunks | `SELECT COUNT(*) FROM llm.chunk` |
| Total embeddings | `SELECT COUNT(*) FROM llm.embedding` |
| Retrieval queries/day | See retention section |
| Average retrieval time | Track in application logs |
| Chunk coverage | Chunks with embeddings / total chunks |

### Health Checks

```sql
-- Check embedding coverage
SELECT 
    (SELECT COUNT(*) FROM llm.embedding) AS embeddings,
    (SELECT COUNT(*) FROM llm.chunk) AS chunks,
    CAST((SELECT COUNT(*) FROM llm.embedding) AS FLOAT) / 
    NULLIF((SELECT COUNT(*) FROM llm.chunk), 0) AS coverage;

-- Check for orphan embeddings
SELECT COUNT(*) AS orphan_embeddings
FROM llm.embedding e
LEFT JOIN llm.chunk c ON e.chunk_id = c.chunk_id
WHERE c.chunk_id IS NULL;
```

---

## Backup and Recovery

### Backup Considerations

Include in backups:
- SQL tables: `llm.chunk`, `llm.embedding`, `llm.retrieval`, `llm.retrieval_hit`
- Lake artifacts: `lake/llm_index/`

### Recovery

Re-indexing is idempotent:
1. Chunks with same ID are upserted
2. Embeddings are deduplicated by (chunk_id, model, vector_hash)
3. Retrieval logs are append-only

To rebuild from scratch:
```bash
# Truncate tables (if needed)
# Re-run full indexing
python -m src.llm.retrieval.indexer \
    --source-manifest sources.json \
    --mode full
```

---

## Related Documentation

- [Retrieval Overview](retrieval.md) — System architecture
- [Indexing Guide](indexing.md) — How to index sources
- [Docker Setup](../runbooks/docker_local_dev.md) — Local development
