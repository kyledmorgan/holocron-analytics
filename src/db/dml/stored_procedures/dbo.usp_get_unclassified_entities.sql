CREATE PROCEDURE [dbo].[usp_get_unclassified_entities]
    @limit INT = 200,
    @fill_missing_only BIT = 0,
    @require_normalization BIT = 0,
    @require_tags BIT = 0
AS
BEGIN
    SET NOCOUNT ON;

    -- Base predicate: active latest entities missing classification.
    -- When @fill_missing_only = 1, also include partially classified rows.
    SELECT TOP (@limit)
        e.EntityKey,
        e.EntityGuid,
        e.DisplayName,
        e.EntityType,
        e.DisplayNameNormalized,
        e.SortName,
        e.AliasCsv,
        e.IsLatest,
        e.IsActive,
        e.ExternalKey,
        e.SourcePageId
    FROM [dbo].[DimEntity] e
    WHERE e.IsLatest = 1
      AND e.IsActive = 1
      AND (
          -- Primary: EntityType is missing
          e.EntityType IS NULL
          -- Or: fill-missing-only mode picks up partial rows
          OR (@fill_missing_only = 1 AND (
              e.DisplayNameNormalized IS NULL
              OR e.SortName IS NULL
          ))
          -- Or: require-normalization makes partially normalized rows eligible
          OR (@require_normalization = 1 AND (
              e.DisplayNameNormalized IS NULL
              OR e.SortName IS NULL
          ))
          -- Or: require-tags makes rows without aliases eligible
          OR (@require_tags = 1 AND e.AliasCsv IS NULL)
      )
    ORDER BY e.EntityKey ASC;
END
