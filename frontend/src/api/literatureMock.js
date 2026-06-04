// 文献知识库的模拟后端接口（路线 A）。
// 用 localStorage 持久化，刷新不丢；接真后端时把这些函数体换成 fetch('/api/...') 即可。
// 接口契约见 docs/页面与交互设计.md 与「上传文献页方案」。

const STORE_KEY = 'asd_documents'
const TAGS = ['行为干预', '语言沟通', '社交训练', '家庭训练', '感觉统合', '综合指南']

const delay = (ms) => new Promise((r) => setTimeout(r, ms))

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || []
  } catch {
    return []
  }
}

function save(docs) {
  localStorage.setItem(STORE_KEY, JSON.stringify(docs))
}

// GET /api/documents —— 已入库文献列表
export async function getDocuments() {
  await delay(150)
  return load()
}

// GET /api/stats —— 知识库概览
export async function getStats() {
  const docs = load()
  return {
    docCount: docs.length,
    chunkCount: docs.reduce((s, d) => s + d.chunks, 0),
  }
}

// DELETE /api/documents/{id}
export async function deleteDocument(id) {
  await delay(200)
  save(load().filter((d) => d.id !== id))
  return { ok: true }
}

// POST /api/documents/ingest —— 上传 + 入库。onProgress 模拟后端流式进度。
// files: File[]；opts: { tag, chunkSize, overlap }
export async function ingestDocuments(files, opts, onProgress) {
  const existing = load()
  const created = []

  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    const emit = (stage, detail) =>
      onProgress?.({ fileIndex: i, total: files.length, filename: f.name, stage, detail })

    emit('抽取', `解析 ${f.name}`)
    await delay(450)

    // 用文件大小粗略估算分块数（仅演示）
    const estChunks = Math.max(1, Math.round(f.size / Math.max(200, opts.chunkSize * 2)))
    emit('分块', `chunk=${opts.chunkSize} 重叠=${opts.overlap}，共 ${estChunks} 块`)
    await delay(350)

    for (let c = 1; c <= estChunks; c++) {
      emit('嵌入', `向量化第 ${c}/${estChunks} 块`)
      await delay(Math.min(120, 600 / estChunks))
    }

    emit('写库', `写入向量库 literature 集合`)
    await delay(300)

    created.push({
      id: `${Date.now()}-${i}-${Math.floor(Math.random() * 1e4)}`,
      filename: f.name,
      tag: opts.tag,
      chunks: estChunks,
      sizeKB: Math.round(f.size / 1024),
      uploadTime: new Date().toISOString(),
    })
  }

  save([...created, ...existing])
  return created
}

export { TAGS }
