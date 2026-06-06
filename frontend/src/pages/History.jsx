import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ConsultAnswer from '../components/ConsultAnswer.jsx'
import {
  loadHistory,
  clearHistory,
  removeHistoryRecord,
  formatTime,
  kindLabel,
  HISTORY_EVENT,
} from '../lib/consultHistory.js'

export default function History() {
  const [records, setRecords] = useState(() => loadHistory())
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    const refresh = () => setRecords(loadHistory())
    window.addEventListener(HISTORY_EVENT, refresh)
    return () => window.removeEventListener(HISTORY_EVENT, refresh)
  }, [])

  const onClear = () => {
    if (!records.length) return
    if (!window.confirm('清空本标签页内的全部咨询记录？关闭浏览器后记录也会消失。')) return
    clearHistory()
    setOpenId(null)
  }

  const onRemove = (id) => {
    if (!window.confirm('删除这条记录？')) return
    removeHistoryRecord(id)
    setOpenId((prev) => (prev === id ? null : prev))
  }

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <h1>咨询历史</h1>
          <p className="history-sub">
            仅保存在当前浏览器标签页，关闭标签后自动清除 · 共 {records.length} 条
          </p>
        </div>
        <div className="history-actions">
          <Link to="/consult" className="btn btn-ghost">去咨询</Link>
          {records.length > 0 && (
            <button type="button" className="btn btn-outline" onClick={onClear}>清空记录</button>
          )}
        </div>
      </div>

      {records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🕘</div>
          <h3>暂无咨询记录</h3>
          <p>在「个案咨询」页提问后，问答会显示在这里，方便你在本标签页内回溯。</p>
          <div className="empty-state-actions">
            <Link to="/consult" className="btn btn-primary">开始咨询</Link>
          </div>
        </div>
      ) : (
        <div className="history-list">
          {records.map((r) => {
            const expanded = openId === r.id
            return (
              <article className={`history-item${expanded ? ' open' : ''}`} key={r.id}>
                <button
                  type="button"
                  className="history-item-head"
                  onClick={() => setOpenId(expanded ? null : r.id)}
                  aria-expanded={expanded}
                >
                  <div className="hi-main">
                    <time className="hi-time">{formatTime(r.ts)}</time>
                    <p className="hi-question">{r.question}</p>
                    <p className="hi-meta">
                      <span className={`hi-tag hi-tag-${r.kind}`}>{kindLabel(r.kind)}</span>
                      <span>{r.config.model} · Top-{r.config.topK}</span>
                      {r.config.enableWebSearch && <span>· 含网络检索</span>}
                      <span>· {r.profileSummary}</span>
                    </p>
                  </div>
                  <span className="hi-chevron" aria-hidden>{expanded ? '▾' : '▸'}</span>
                </button>

                {expanded && (
                  <div className="history-item-body">
                    <div className="hi-user-q">
                      <span className="hi-label">提问</span>
                      <p>{r.question}</p>
                    </div>
                    <div className="hi-answer">
                      <span className="hi-label">回答</span>
                      <div className="bubble bubble-bot">
                        <ConsultAnswer data={r.answer} />
                      </div>
                    </div>
                    <button type="button" className="hi-remove" onClick={() => onRemove(r.id)}>
                      删除此条
                    </button>
                  </div>
                )}
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
