CREATE VIEW [sem].[vw_PagesByType]
AS
SELECT
    pc.primary_type,
    pc.taxonomy_version,
    COUNT(*) AS page_count,
    AVG(CAST(pc.confidence_score AS FLOAT)) AS avg_confidence,
    SUM(CASE WHEN pc.needs_review = 1 THEN 1 ELSE 0 END) AS needs_review_count,
    SUM(CASE WHEN pc.method = 'rules' THEN 1 ELSE 0 END) AS rules_count,
    SUM(CASE WHEN pc.method = 'llm' THEN 1 ELSE 0 END) AS llm_count,
    SUM(CASE WHEN pc.method = 'hybrid' THEN 1 ELSE 0 END) AS hybrid_count
FROM [sem].[PageClassification] pc
INNER JOIN [sem].[SourcePage] sp
    ON pc.source_page_id = sp.source_page_id
    AND sp.is_active = 1
WHERE pc.is_current = 1
GROUP BY pc.primary_type, pc.taxonomy_version;
