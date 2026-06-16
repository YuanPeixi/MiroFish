import service from './index'

export const getNarrativeState = (projectId, branchId = null) => {
  const params = {}
  if (branchId) params.branch_id = branchId
  return service.get(`/api/narrative/state/${projectId}`, { params })
}

export const createNarrativeSnapshot = (data) => {
  return service.post('/api/narrative/snapshot', data)
}

export const rollbackNarrativeSnapshot = (data) => {
  return service.post('/api/narrative/rollback', data)
}

export const deriveNarrativeBranch = (data) => {
  return service.post('/api/narrative/branch/derive', data)
}

export const advanceNarrativeBranch = (data) => {
  return service.post('/api/narrative/branch/advance', data)
}

export const scoreNarrativeBranches = (data) => {
  return service.post('/api/narrative/branches/score', data)
}

export const selectNarrativeEnding = (data) => {
  return service.post('/api/narrative/ending/select', data)
}

export const exportNarrativeScript = (projectId, branchId = null) => {
  const params = {}
  if (branchId) params.branch_id = branchId
  return service.get(`/api/narrative/export/${projectId}`, { params })
}
