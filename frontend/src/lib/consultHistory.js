const STORAGE_KEY = 'asd_consult_history'
export const HISTORY_EVENT = 'consult-history-changed'

function notify() {
  window.dispatchEvent(new CustomEvent(HISTORY_EVENT))
}

export function summarizeProfile(profile) {
  if (!profile) return '未提供个案信息'
  const parts = []
  if (profile.age) parts.push(profile.age)
  if (profile.coreSymptoms?.length) {
    const shown = profile.coreSymptoms.slice(0, 3).join('、')
    parts.push(profile.coreSymptoms.length > 3 ? `${shown}…` : shown)
  }
  return parts.length ? parts.join(' · ') : '已填写个案（未填年龄/表现）'
}

export function answerKind(data) {
  if (data?.error) return 'error'
  if (data?.refused) return 'refused'
  if (data?.insufficientLiterature) return 'insufficient'
  if (data?.literatureMissing) return 'literatureMissing'
  return 'answer'
}

export function kindLabel(kind) {
  switch (kind) {
    case 'refused': return '已拒答'
    case 'insufficient': return '文献不足'
    case 'literatureMissing': return '仅网络补充'
    case 'error': return '请求失败'
    default: return '已回答'
  }
}

export function loadHistory() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const list = JSON.parse(raw)
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function saveHistory(list) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  notify()
}

export function addHistoryRecord({ question, profile, config, answer }) {
  const record = {
    id: crypto.randomUUID(),
    ts: Date.now(),
    question,
    profileSummary: summarizeProfile(profile),
    config: {
      model: config?.model || '',
      topK: config?.topK ?? 4,
      enableWebSearch: Boolean(config?.enableWebSearch),
    },
    kind: answerKind(answer),
    answer,
  }
  const list = [record, ...loadHistory()]
  saveHistory(list)
  return record
}

export function removeHistoryRecord(id) {
  saveHistory(loadHistory().filter((r) => r.id !== id))
}

export function clearHistory() {
  sessionStorage.removeItem(STORAGE_KEY)
  notify()
}

export function formatTime(ts) {
  const d = new Date(ts)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
