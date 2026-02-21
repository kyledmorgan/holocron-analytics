/*******************************************************************************
 * VIEW: sem.vw_work
 *
 * PURPOSE: Canonical semantic view over published works (films, series, etc.).
 *          Flattens work information with franchise context.
 *
 * AUDIENCE: Analysts, downstream marts, and learning layer views.
 *
 * KEY COLUMNS:
 *   - WorkKey: Surrogate key for joins
 *   - WorkGuid: Stable external identifier
 *   - WorkTitle: Human-readable title
 *   - WorkCode: Short code (e.g., 'ANH', 'TPM')
 *   - WorkType: Category (Film, Series, etc.)
 *   - FranchiseName: Parent franchise name
 *
 * NOTES: Only returns active, latest version records.
 ******************************************************************************/
CREATE   VIEW sem.vw_work
AS
SELECT
    w.WorkKey,
    w.WorkGuid,
    w.FranchiseKey,
    f.Name                      AS FranchiseName,
    w.WorkType,
    w.Title                     AS WorkTitle,
    w.TitleSort,
    w.EditionOrCut,
    w.WorkCode,
    w.SeasonEpisode,
    w.SeasonNumber,
    w.EpisodeNumber,
    w.VolumeOrIssue,
    w.ReleaseDate,
    w.ReleaseDatePrecision,
    w.ReleaseRegion,
    w.RuntimeRef,
    w.SynopsisShort,
    w.Notes,
    w.ValidFromUtc
FROM dbo.DimWork w
INNER JOIN dbo.DimFranchise f
    ON w.FranchiseKey = f.FranchiseKey
   AND f.IsActive = 1
   AND f.IsLatest = 1
WHERE w.IsActive = 1
  AND w.IsLatest = 1;
