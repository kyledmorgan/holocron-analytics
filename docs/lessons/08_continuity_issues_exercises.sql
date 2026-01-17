/******************************************************************************
 * MODULE 08: Continuity Issues & Claims
 * 
 * OBJECTIVE: Explore continuity conflicts and the claims that support or
 *            contradict canonical facts.
 * 
 * SKILLS PRACTICED:
 *   - Complex filtering
 *   - Multi-table analysis
 *   - Status and severity analysis
 *   - Evidence-based reasoning
 * 
 * TABLES USED: learn_continuity_issues, learn_claims
 * 
 * DIFFICULTY: Intermediate-Advanced
 ******************************************************************************/

-- ============================================================================
-- EXERCISE 1: Explore Continuity Issues
-- ============================================================================
-- GOAL: Preview the continuity issues table to understand available data.
-- 
-- HINTS:
--   - Look at Severity, DisputeLevel, Status columns
--   - These are canon conflicts and ambiguities
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:




-- ============================================================================
-- EXERCISE 2: Issues by Severity
-- ============================================================================
-- GOAL: Count continuity issues by severity level.
--       Which severity is most common?
-- 
-- HINTS:
--   - GROUP BY Severity
--   - Severity levels: Low, Med, High, Critical
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:




-- ============================================================================
-- EXERCISE 3: High Severity Issues
-- ============================================================================
-- GOAL: List all High or Critical severity issues.
--       Show summary, dispute level, and status.
-- 
-- HINTS:
--   - Filter on Severity IN ('High', 'Critical')
--   - Order by SeverityScore DESC
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:




-- ============================================================================
-- EXERCISE 4: Issue Status Analysis
-- ============================================================================
-- GOAL: Count issues by status (Open, Explained, Retconned, etc.).
--       What percentage are resolved vs. open?
-- 
-- HINTS:
--   - GROUP BY Status
--   - Calculate percentage of total
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:




-- ============================================================================
-- EXERCISE 5: Issues by Work
-- ============================================================================
-- GOAL: Find which works have the most continuity issues.
-- 
-- HINTS:
--   - GROUP BY WorkTitle
--   - Some issues may not be tied to a specific work
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:




-- ============================================================================
-- EXERCISE 6: Explore Claims
-- ============================================================================
-- GOAL: Preview the claims table to understand fact assertions.
-- 
-- HINTS:
--   - Claims are atomic assertions about entities
--   - Look at SubjectName, Predicate, Value columns
-- 
-- TABLES: learn_claims

-- Write your query below:




-- ============================================================================
-- EXERCISE 7: Claims by Subject
-- ============================================================================
-- GOAL: Count claims per subject entity.
--       Who has the most claims about them?
-- 
-- HINTS:
--   - GROUP BY SubjectName
--   - These are characters, locations, etc.
-- 
-- TABLES: learn_claims

-- Write your query below:




-- ============================================================================
-- EXERCISE 8: Low Confidence Claims
-- ============================================================================
-- GOAL: Find claims with low confidence (< 0.70).
--       These might be uncertain or disputed facts.
-- 
-- HINTS:
--   - Filter on ConfidenceScore < 0.70
--   - Show subject, predicate, value, and confidence
-- 
-- TABLES: learn_claims

-- Write your query below:




-- ============================================================================
-- EXERCISE 9: Claim Types
-- ============================================================================
-- GOAL: Count claims by ClaimType (Attribute, Relationship, etc.).
-- 
-- HINTS:
--   - GROUP BY ClaimType
--   - Also show average confidence per type
-- 
-- TABLES: learn_claims

-- Write your query below:




-- ============================================================================
-- EXERCISE 10: Disputed Topics
-- ============================================================================
-- GOAL: Find high-dispute issues (DisputeLevel = 'High') and their details.
--       These are the most controversial canon points.
-- 
-- HINTS:
--   - Filter on DisputeLevel = 'High'
--   - Show full context including work and scene if available
-- 
-- TABLES: learn_continuity_issues

-- Write your query below:



