import { useState, useEffect, useRef } from 'react'
import { getDocuments, getStats, deleteDocument, ingestDocuments, TAGS } from '../api/literatureMock.js'

function fmtTime(iso) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default function Literature() {
  const [docs, setDocs] = useState([])
  const [stats, setStats] = useState({ docCount: 0, chunkCount: 0 })
  const [pending, setPending] = useState([])
  const [tag, setTag] = useState(TAGS[0])
  const [chunkSize, setChunkSize] = useState(500)
  const [overlap, setOverlap] = useState(80)
  const [ingesting, setIngesting] = useState(false)
  const [progress, setProgress] = useState(null) // {fileIndex,total,filename,stage,detail}
  const [logs, setLogs] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef(null)

  const refresh = async () => {
    setDocs(await getDocuments())
    setStats(await getStats())
  }
  useEffect(() => { refresh() }, [])

  const addFiles = (fileList) => {
    const arr = Array.from(fileList)
    // 按文件名去重
    setPending((prev) => {
      const names = new Set(prev.map((f) => f.name))
      return [...prev, ...arr.filter((f) => !names.has(f.name))]
    })
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files)
  }

  const removePending = (name) => setPending((prev) => prev.filter((f) => f.name !== name))

  const startIngest = async () => {
    if (!pending.length || ingesting) return
    setIngesting(true)
    setLogs([])
    await ingestDocuments(
      pending,
      { tag, chunkSize: Number(chunkSize), overlap: Number(overlap) },
      (p) => {
        setProgress(p)
        setLogs((prev) => [`[${p.fileIndex + 1}/${p.total}] ${p.stage}：${p.detail}`, ...prev].slice(0, 60))
      },
    )
    setIngesting(false)
    setProgress(null)
    setPending([])
    await refresh()
  }

  const onDelete = async (doc) => {
    if (!window.confirm(`确认从知识库删除「${doc.filename}」？将同时移除其 ${doc.chunks} 个向量片段。`)) return
    await deleteDocument(doc.id)
    await refresh()
  }

  const pct = progress ? Math.round(((progress.fileIndex) / progress.total) * 100) : 0

  return (
    <div className="lit-page">
      <div className="lit-header">
        <div>
          <h1>文献知识库</h1>
          <p className="lit-sub">上传权威文献构建可检索、可溯源的知识库（离线入库链路）</p>
        </div>
        <div className="lit-stats">
          <span><b>{stats.docCount}</b> 篇文献</span>
          <span className="sep">·</span>
          <span><b>{stats.chunkCount}</b> 个片段</span>
        </div>
      </div>

      <div className="lit-grid">
        {/* 左：上传与入库 */}
        <div className="upload-panel">
          <div
            className={`dropzone ${dragOver ? 'over' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <div className="dz-icon">⬆</div>
            <div className="dz-text">拖拽文件到此，或<span>点击选择</span></div>
            <div className="dz-hint">支持 PDF / Word / txt，可多选 · 请上传权威来源（指南、同行评议文献）</div>
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.doc,.docx,.txt"
              hidden
              onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
            />
          </div>

          {pending.length > 0 && (
            <div className="pending">
              <div className="pending-title">待入库（{pending.length}）</div>
              {pending.map((f) => (
                <div className="pending-item" key={f.name}>
                  <span className="pi-name" title={f.name}>📄 {f.name}</span>
                  <span className="pi-size">{Math.round(f.size / 1024)} KB</span>
                  {!ingesting && <button className="pi-remove" onClick={() => removePending(f.name)}>移除</button>}
                </div>
              ))}
            </div>
          )}

          <div className="config">
            <label>分类标签
              <select value={tag} onChange={(e) => setTag(e.target.value)} disabled={ingesting}>
                {TAGS.map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <div className="config-row">
              <label>chunk 大小
                <input type="number" min="100" step="50" value={chunkSize}
                  onChange={(e) => setChunkSize(e.target.value)} disabled={ingesting} />
              </label>
              <label>重叠
                <input type="number" min="0" step="10" value={overlap}
                  onChange={(e) => setOverlap(e.target.value)} disabled={ingesting} />
              </label>
            </div>
            <p className="config-hint">分块大小与重叠是检索效果的主旋钮，可作为对比实验变量。</p>
          </div>

          <button className="btn btn-primary btn-block" onClick={startIngest} disabled={!pending.length || ingesting}>
            {ingesting ? '入库中…' : `开始入库${pending.length ? `（${pending.length}）` : ''}`}
          </button>

          {ingesting && (
            <div className="progress">
              <div className="progress-bar"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
              <div className="progress-now">{progress?.stage}：{progress?.detail}</div>
            </div>
          )}
          {logs.length > 0 && (
            <div className="log">
              {logs.map((l, i) => <div key={i} className="log-line">{l}</div>)}
            </div>
          )}
        </div>

        {/* 右：已入库列表 */}
        <div className="doc-panel">
          {docs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📚</div>
              <h3>知识库还是空的</h3>
              <p>先在左侧上传第一篇权威文献，个案咨询才能有据可查。</p>
            </div>
          ) : (
            <div className="doc-list">
              <div className="doc-row doc-head">
                <span>文献</span><span>标签</span><span>片段</span><span>入库时间</span><span></span>
              </div>
              {docs.map((d) => (
                <div className="doc-row" key={d.id}>
                  <span className="doc-name" title={d.filename}>📄 {d.filename}</span>
                  <span><em className="tag-chip">{d.tag}</em></span>
                  <span>{d.chunks}</span>
                  <span className="doc-time">{fmtTime(d.uploadTime)}</span>
                  <span><button className="doc-del" onClick={() => onDelete(d)} title="删除">🗑</button></span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
