const MAX_HISTORY_TURNS = 5

/** 将助手回复压缩为摘要，供多轮 history 传给后端 */
export function summarizeAnswer(data) {
  if (!data) return ''
  if (data.error) return `（出错：${data.error}）`
  if (data.refused) return data.answer || '（该问题已拒答并转介）'
  if (data.insufficientLiterature) {
    return data.suggestions?.[0]?.text || '（文献不足，暂无法给出循证建议）'
  }
  const parts = (data.suggestions || []).map((s) => s.text).filter(Boolean)
  const text = parts.slice(0, 3).join('；')
  return text.length > 320 ? `${text.slice(0, 320)}…` : text || '（无建议）'
}

/** 从已完成的消息列表构建 API history（不含当前待发问题） */
export function buildApiHistory(messages) {
  const turns = []
  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i]
    if (msg.role !== 'user') continue
    const next = messages[i + 1]
    if (next?.role !== 'assistant') continue
    turns.push({
      question: msg.text,
      answerSummary: summarizeAnswer(next.data),
    })
  }
  return turns.slice(-MAX_HISTORY_TURNS)
}

export function countTurns(messages) {
  return messages.filter((m) => m.role === 'user').length
}
