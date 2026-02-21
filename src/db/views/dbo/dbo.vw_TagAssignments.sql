CREATE VIEW [dbo].[vw_TagAssignments]
AS
SELECT
    ta.AssignmentId,
    t.TagKey,
    t.TagType,
    t.TagName,
    t.DisplayName AS TagDisplayName,
    t.Visibility AS TagVisibility,
    ta.TargetType,
    ta.TargetId,
    ta.Weight,
    ta.Confidence,
    ta.AssignmentMethod,
    ta.AssignedUtc
FROM [dbo].[BridgeTagAssignment] ta
INNER JOIN [dbo].[DimTag] t ON ta.TagKey = t.TagKey
WHERE ta.IsActive = 1
    AND t.IsActive = 1
    AND t.IsLatest = 1;
