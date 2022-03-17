---------------------------------------------------------------------------------------------------
--  @author:         Alex Gheith
--  @copyright:      Copyright 2021, Neuro-developmental Disorders Lab (NDD), Purdue University
--  @status:         Production
--  @Description:    These are a set of common queries that admins need to run. Most of them
--                   returns some results from the database, but some will alter the DB.
---------------------------------------------------------------------------------------------------

-- ################################################################################################
-- Sample Pool Queries
-- ################################################################################################

-- Get the number of available samples left to code.
-- ------------------------------------------------------------------------------------------------
SELECT COUNT(*)
FROM "Main"."UtteranceSamplePool"
WHERE "CoderID" IS NULL;


-- Get the number of orphaned samples (samples that were started by a coder, but not finished.)
-- ------------------------------------------------------------------------------------------------
SELECT *
FROM "Main"."UtteranceSamplePool"
WHERE "IsProcessing"
AND "ModifiedOn" <= (NOW() - interval '1 hour')
ORDER BY "ModifiedOn";


-- Release orphaned samples. 
--      NOTE: Run on a daily.
-- ------------------------------------------------------------------------------------------------
--UPDATE "Main"."UtteranceSamplePool"
--SET "IsProcessing" = FALSE
--WHERE "IsProcessing"
--AND "ModifiedOn" <= (NOW() - interval '1 hours');


-- ################################################################################################
-- Log Analysis Queries
-- ################################################################################################

-- Get the number of lines in the LogEntry table for the past month from the current date.
-- ------------------------------------------------------------------------------------------------
SELECT COUNT (*)
FROM "Main"."LogEntry" AS l
WHERE l."TimeStamp" <= (NOW() - interval '1 month');


-- Delete the lines in the LogEntry table for the past month from the current date.
--      NOTE: Run every couple of months.
-- ------------------------------------------------------------------------------------------------
--DELETE
--FROM "Main"."LogEntry" AS l
--WHERE l."TimeStamp" <= (NOW() - interval '1 month')


-- Get the number of lines in the LogEntry after a certain date.
--      NOTE: Modify the date in the quoted value per your need.
-- ------------------------------------------------------------------------------------------------
SELECT COUNT(*)
FROM "Main"."LogEntry" AS l
WHERE l."TimeStamp" > '2021-02-01'; 


-- Get the lines showing possible errors in the LogEntry after a certain date.
--      NOTE: Modify the date in the quoted value per your need.
-- ------------------------------------------------------------------------------------------------
SELECT l.*
FROM "Main"."LogEntry" AS l
WHERE l."TimeStamp" > '2021-02-24'
AND (l."Level" = 'ERROR' OR l."Level" = 'CRITICAL')
ORDER BY l."TimeStamp" DESC;


-- ################################################################################################
-- Coding Progress Queries
-- ################################################################################################

-- Get the number of codes finishes per day, after a certain date, or between two date.
--      NOTE: * Modify the first date to be the last day of the previous year.
--            * Modify the Start and/or the End dates in per your need.
--            * Uncomment the End date if you want to use it.
-- ------------------------------------------------------------------------------------------------
SELECT date '2020-12-31' + EXTRACT(DOY FROM uc."ModifiedOn")::integer AS "Day"
       , COUNT(EXTRACT(DOY FROM uc."ModifiedOn")) AS "CodesPerDay"
FROM "Main"."UtteranceCoding" AS uc
WHERE uc."ModifiedOn" >= '2021-01-01'       -- Start Date
-- AND uc."ModifiedOn" <= '2021-04-21'      -- End Date
GROUP BY EXTRACT(DOY FROM uc."ModifiedOn")::integer
ORDER BY "Day";


-- Get the number of codes finished per user after a certain date, or between two date.
--      NOTE: * Modify the Start and/or the End dates in per your need.
--            * Uncomment the End date if you want to use it.
-- ------------------------------------------------------------------------------------------------
SELECT u."FirstName", u."LastName", COUNT(uc."CoderID") AS "CodesPerCoder"
FROM "Main"."UtteranceCoding" AS uc
INNER JOIN "Main"."User" AS u
    ON uc."CoderID" = u."UserID"
WHERE uc."ModifiedOn" >= '2021-01-01'       -- Start Date 
-- AND uc."ModifiedOn" <= '2021-04-21'      -- End Date
GROUP BY uc."CoderID", u."FirstName", u."LastName"
ORDER BY "CodesPerCoder" DESC;


-- Get all codes finished after a certain date, or between two date.
--      NOTE: * Modify the Start and/or the End dates in per your need.
--            * Uncomment the End date if you want to use it.
-- ------------------------------------------------------------------------------------------------
SELECT *
FROM "Main"."UtteranceCoding" AS uc
INNER JOIN "Main"."User" AS u
    ON uc."CoderID" = u."UserID"
INNER JOIN "Main"."UtteranceTypeAnnotation" AS ua
    ON uc."UtteranceTypeAnnotationID" = ua."UtteranceTypeAnnotationID"
INNER JOIN "Main"."UtteranceType" AS ut
    ON ua."UtteranceTypeID" = ut."UtteranceTypeID"
WHERE uc."ModifiedOn" > '2020-05-17'       -- Start Date
-- AND uc."ModifiedOn" < '2020-05-17'      -- End Date
ORDER BY uc."AddedOn" DESC;


-- Get data needed for calculating coding rate.
-- Get all codes finished after a certain date, or between two date, along with coding timestamps.
--      NOTE: * Modify the Start and/or the End dates in per your need.
--            * Uncomment the End date if you want to use it.
-- ------------------------------------------------------------------------------------------------
SELECT uc."UtteranceID", u."FirstName", u."LastName", uc."CoderID", r."AssessmentID", uc."AddedOn"
FROM "Main"."UtteranceCoding" AS uc
INNER JOIN "Main"."User" AS u
    ON uc."CoderID" = u."UserID"
INNER JOIN "Main"."Utterance" AS ut
    ON uc."UtteranceID" = ut."UtteranceID"
INNER JOIN "Main"."Segment" AS s
    ON ut."SegmentID" = s."SegmentID"
INNER JOIN "Main"."Recording" AS r
    ON s."RecordingID" = r."RecordingID"
WHERE uc."Comments" IS NULL OR uc."Comments" <> 'Legacy Code'
AND uc."ModifiedOn" > '2020-09-01'         -- Start Date
-- AND uc."ModifiedOn" < '2020-10-17'      -- End Date
ORDER BY u."FirstName", u."LastName", uc."AddedOn";


-- ################################################################################################
-- Analysis of the current recordings in the DB.
-- ################################################################################################

SELECT    r."RecordingID"
        , rt."Description" AS "RecordingType"
        , r."AssessmentID"
        , p."ChildID"
        , r."RecordingDate"
        , r."IsValid" AS "IsValidRecording"
        , (SELECT COUNT(s2."SegmentID")
           FROM "Main"."Segment" AS s2
           WHERE s2."RecordingID" = r."RecordingID") AS "TotalSegments"
        , (SELECT COUNT(s2."SegmentID")
           FROM "Main"."Segment" AS s2
           WHERE s2."RecordingID" = r."RecordingID"
           AND s2."IsSelected") AS "SelectedSegments"
        , (SELECT COUNT(s2."SegmentID")
           FROM "Main"."Segment" AS s2
           WHERE s2."RecordingID" = r."RecordingID"
           AND s2."IsSelected"
           AND s2."SelectionCriterionID" = 100) AS "Segments (HV)"
        , (SELECT COUNT(s2."SegmentID")
           FROM "Main"."Segment" AS s2
           WHERE s2."RecordingID" = r."RecordingID"
           AND s2."IsSelected"
           AND s2."SelectionCriterionID" = 200) AS "Segment (RS)"

        , (SELECT COUNT(u2."UtteranceID")
           FROM "Main"."Utterance" AS u2
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID") AS "Utterances"
        , (SELECT COUNT(u2."UtteranceID")
           FROM "Main"."Utterance" AS u2
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID"
           AND s3."SelectionCriterionID" = 100) AS "Utterances (HV)"
        , (SELECT COUNT(u2."UtteranceID")
           FROM "Main"."Utterance" AS u2
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID"
           AND s3."SelectionCriterionID" = 200) AS "Utterances (RS)"

        , (SELECT COUNT(uc2."UtteranceCodingID")
           FROM "Main"."UtteranceCoding" AS uc2
           INNER JOIN "Main"."Utterance" AS u2
                ON uc2."UtteranceID" = u2."UtteranceID"
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID" AND uc2."IsAcceptable") AS "TotalUtteranceCodes"
        , (SELECT COUNT(uc2."UtteranceCodingID")
           FROM "Main"."UtteranceCoding" AS uc2
           INNER JOIN "Main"."Utterance" AS u2
                ON uc2."UtteranceID" = u2."UtteranceID"
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID"
           AND s3."SelectionCriterionID" = 100 AND uc2."IsAcceptable") AS "UtteranceCodes (HV)"
        , (SELECT COUNT(uc2."UtteranceCodingID")
           FROM "Main"."UtteranceCoding" AS uc2
           INNER JOIN "Main"."Utterance" AS u2
                ON uc2."UtteranceID" = u2."UtteranceID"
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID"
           AND s3."SelectionCriterionID" = 200 AND uc2."IsAcceptable") AS "UtteranceCodes (RS)"
        , (SELECT COUNT(usp."UtteranceID")
           FROM "Main"."UtteranceSamplePool" AS usp
           INNER JOIN "Main"."Utterance" AS u2
                ON usp."UtteranceID" = u2."UtteranceID"
           INNER JOIN "Main"."Segment" AS s3
                ON u2."SegmentID" = s3."SegmentID"
           WHERE s3."RecordingID" = r."RecordingID"
           AND usp."CoderID" IS NULL) AS "RemainingCodesInQueue"
FROM "Main"."Recording" AS r
INNER JOIN "Main"."RecordingType" AS rt
    ON r."RecordingTypeID" = rt."RecordingTypeID"
INNER JOIN "Main"."Participant" AS p
    ON r."ParticipantID" = p."ParticipantID"
INNER JOIN "Main"."Sex" AS sx
    ON p."SexID" = sx."SexID"
INNER JOIN "Main"."GeneticRisk" AS gr
    ON p."GeneticRiskID" = gr."GeneticRiskID"
WHERE rt."Description" = 'Home'
ORDER BY r."RecordingID";
