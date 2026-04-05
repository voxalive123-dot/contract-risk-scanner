const API_BASE = "http://localhost:8000"

export async function analyzeContract(text: string, apiKey: string) {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({
      text: text,
    }),
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`API error: ${error}`)
  }

  return response.json()
}