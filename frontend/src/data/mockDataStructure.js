/**
 * Future mock data contract for the CMPDI/CIL Mining Intelligence Platform.
 *
 * documents: [{
 *   id,
 *   title,
 *   docType,
 *   source,
 *   status,
 *   mineId,
 *   subsidiaryId,
 *   uploadedAt,
 *   tags,
 *   summary
 * }]
 *
 * subsidiaries: [{
 *   id,
 *   name,
 *   region,
 *   mines,
 *   headOffice
 * }]
 *
 * mines: [{
 *   id,
 *   name,
 *   subsidiaryId,
 *   location,
 *   productionStage,
 *   status,
 *   lastUpdated
 * }]
 *
 * reports: [{
 *   id,
 *   title,
 *   type,
 *   generatedAt,
 *   createdBy,
 *   filters,
 *   summary
 * }]
 *
 * queries: [{
 *   id,
 *   userId,
 *   question,
 *   category,
 *   context,
 *   answerSummary,
 *   status
 * }]
 */

export const mockDataStructure = {
  documents: [],
  subsidiaries: [],
  mines: [],
  reports: [],
  queries: [],
}

export default mockDataStructure
