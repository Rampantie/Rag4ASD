// 个案咨询真实 API（FastAPI + DeepSeek）

export const MODELS = ['DeepSeek-V3', '智谱 GLM-4', 'Qwen-Max']

async function parseJson(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    const detail = err.detail
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join('; ')
      : detail || res.statusText || '请求失败'
    throw new Error(message)
  }
  return res.json()
}

// POST /api/case/profile
export async function extractProfile(file, onProgress) {
  onProgress?.({ stage: '抽取', detail: `解析 ${file.name}` })
  const form = new FormData()
  form.append('file', file)

  const res = await fetch('/api/case/profile', { method: 'POST', body: form })
  const data = await parseJson(res)
  onProgress?.({ stage: '提炼', detail: '请根据报告内容填写个案画像' })
  return data
}

// POST /api/case/ask
export async function askQuestion({ question, profile, config }, onProgress) {
  onProgress?.({ stage: '安全护栏', detail: '校验问题风险等级' })

  onProgress?.({ stage: '检索', detail: `从文献库召回 Top-${config.topK} 相关片段` })
  if (config.enableWebSearch) {
    onProgress?.({ stage: '网络检索', detail: 'Tavily 补充查询相关背景…' })
  }

  const res = await fetch('/api/case/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      profile,
      config: {
        model: config.model,
        topK: config.topK,
        enableWebSearch: Boolean(config.enableWebSearch),
      },
    }),
  })

  onProgress?.({ stage: '生成', detail: `${config.model} 综合文献与网络参考组织建议` })
  return parseJson(res)
}
