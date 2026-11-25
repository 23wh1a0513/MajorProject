export async function apiRequest(path, options = {}) {
  let response
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(sessionStorage.getItem('sco-demo-token')
          ? { Authorization: `Bearer ${sessionStorage.getItem('sco-demo-token')}` }
          : {}),
        ...options.headers,
      },
    })
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Backend is unreachable. Start it with npm run backend.')
    }
    throw error
  }

  let body
  try {
    body = await response.json()
  } catch {
    throw new Error('Backend returned an invalid response.')
  }
  if (!response.ok) {
    const error = new Error(body.error || `Backend request failed (${response.status}).`)
    error.status = response.status
    throw error
  }
  return body
}
