// 文献知识库真实 API（FastAPI 后端）

const TAGS = ['行为干预', '语言沟通', '社交训练', '家庭训练', '感觉统合', '综合指南']

async function parseJson(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText || '请求失败')
  }
  return res.json()
}

// GET /api/documents
export async function getDocuments() {
  return parseJson(await fetch('/api/documents'))
}

// GET /api/stats
export async function getStats() {
  return parseJson(await fetch('/api/stats'))
}

// DELETE /api/documents/{id}
export async function deleteDocument(id) {
  return parseJson(await fetch(`/api/documents/${id}`, { method: 'DELETE' }))
}

// POST /api/documents/ingest — SSE 进度流
export async function ingestDocuments(files, opts, onProgress) {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  form.append('tag', opts.tag)
  form.append('chunk_size', String(opts.chunkSize))
  form.append('overlap', String(opts.overlap))

  const res = await fetch('/api/documents/ingest', { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText || '入库失败')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let created = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const payload = JSON.parse(line.slice(5).trim())
      if (payload.error) throw new Error(payload.message || '入库失败')
      if (payload.done) {
        created = payload.created || []
        continue
      }
      onProgress?.(payload)
    }
  }

  return created
}

export { TAGS }
