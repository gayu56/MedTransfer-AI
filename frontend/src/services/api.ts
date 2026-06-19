const BASE_URL = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || 'Request failed')
  }
  return res.json()
}

// Patients
export const fetchPatients = (search?: string) =>
  request<any>(`/patients${search ? `?search=${encodeURIComponent(search)}` : ''}`)

export const fetchPatient = (id: string) =>
  request<any>(`/patients/${id}`)

// Facilities
export const fetchFacilities = () =>
  request<any>('/facilities')

export const fetchFacility = (id: string) =>
  request<any>(`/facilities/${id}`)

// Transfers
export const fetchTransfers = (status?: string) =>
  request<any>(`/transfers${status ? `?status=${status}` : ''}`)

export const fetchTransfer = (id: string) =>
  request<any>(`/transfers/${id}`)

export const createTransfer = (data: any) =>
  request<any>('/transfers', { method: 'POST', body: JSON.stringify(data) })

export const acceptTransfer = (id: string, data: any) =>
  request<any>(`/transfers/${id}/accept`, { method: 'POST', body: JSON.stringify(data) })

export const declineTransfer = (id: string, data: any) =>
  request<any>(`/transfers/${id}/decline`, { method: 'POST', body: JSON.stringify(data) })

export const updateTransferStatus = (id: string, data: any) =>
  request<any>(`/transfers/${id}/status`, { method: 'PATCH', body: JSON.stringify(data) })

// Compliance
export const fetchCompliance = (transferId: string) =>
  request<any>(`/compliance/${transferId}`)

export const updateCompliance = (transferId: string, data: any) =>
  request<any>(`/compliance/${transferId}`, { method: 'PATCH', body: JSON.stringify(data) })

export const checkCanDispatch = (transferId: string) =>
  request<any>(`/compliance/${transferId}/can-dispatch`)

export const checkCanBroadcast = (transferId: string) =>
  request<any>(`/compliance/${transferId}/can-broadcast`)

// AI Agent
export const chatWithAgent = (data: any) =>
  request<any>('/agent/chat', { method: 'POST', body: JSON.stringify(data) })

export const generateSBAR = (data: any) =>
  request<any>('/agent/sbar/generate', { method: 'POST', body: JSON.stringify(data) })

export const reviewSBAR = (sbarId: string, data: { situation?: string; background?: string; assessment?: string; recommendation?: string; approved: boolean }) =>
  request<any>(`/agent/sbar/${sbarId}/review`, { method: 'PATCH', body: JSON.stringify(data) })

// Calls
export const fetchCallsForTransfer = (transferId: string) =>
  request<any[]>(`/calls/transfer/${transferId}`)

export const createCallLog = (data: any) =>
  request<any>('/calls', { method: 'POST', body: JSON.stringify(data) })

export const updateCallLog = (callId: string, data: any) =>
  request<any>(`/calls/${callId}`, { method: 'PATCH', body: JSON.stringify(data) })

export const generateCallScript = (data: { transfer_id: string; facility_id: string }) =>
  request<any>('/calls/script', { method: 'POST', body: JSON.stringify(data) })

export const runAutoCall = (transferId: string) =>
  request<any>(`/calls/auto-call/${transferId}`, { method: 'POST' })

// Phase 1 AI audio agent: calls facilities, records transcripts, proposes acceptances
export const runAICall = (transferId: string) =>
  request<any>(`/calls/ai-call/${transferId}`, { method: 'POST' })

export const confirmAcceptance = (data: { call_id: string; accepting_physician: string; contact_name?: string; contact_role?: string; notes?: string }) =>
  request<any>('/calls/confirm-acceptance', { method: 'POST', body: JSON.stringify(data) })

// Analytics
export const fetchAnalytics = () =>
  request<any>('/analytics/transfers')
