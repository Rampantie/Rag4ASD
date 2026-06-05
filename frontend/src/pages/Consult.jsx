import { useState, useEffect, useRef } from 'react'
import { extractProfile, askQuestion, MODELS } from '../api/consult.js'
import ConsultAnswer from '../components/ConsultAnswer.jsx'
import { addHistoryRecord } from '../lib/consultHistory.js'

// 把「年龄 / 核心表现 / 既往评估」做成可编辑画像，供用户按孩子真实情况修正后再提问
function emptyProfile() {
  return { sourceName: '', age: '', coreSymptoms: [], assessments: [], note: '' }
}

export default function Consult() {
  const [profile, setProfile] = useState(null)
  const [extracting, setExtracting] = useState(false)
  const [extractStage, setExtractStage] = useState('')
  const [messages, setMessages] = useState([]) // {role, ...}
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [thinkStage, setThinkStage] = useState(null) // {stage, detail}
  const [model, setModel] = useState(MODELS[0])
  const [topK, setTopK] = useState(4)
  const [enableWebSearch, setEnableWebSearch] = useState(false)
  const fileRef = useRef(null)
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const onPickReport = async (file) => {
    if (!file) return
    setExtracting(true)
    try {
      const p = await extractProfile(file, (e) => setExtractStage(`${e.stage}：${e.detail}`))
      setProfile(p)
    } catch (err) {
      window.alert(`报告解析失败：${err.message}`)
    } finally {
      setExtracting(false)
      setExtractStage('')
    }
  }

  const startManualProfile = () => {
    setProfile({ ...emptyProfile(), sourceName: '手动填写', note: '未上传报告，请填写孩子的年龄、核心表现与既往评估。' })
  }

  const updateProfile = (patch) => setProfile((prev) => ({ ...(prev || emptyProfile()), ...patch }))

  const clearSession = () => {
    if (!messages.length && !profile) return
    if (!window.confirm('清空本次会话？将删除个案画像与全部对话（隐私不残留）。')) return
    setProfile(null)
    setMessages([])
  }

  const send = async () => {
    const q = input.trim()
    if (!q || thinking) return
    const config = { model, topK, enableWebSearch }
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: q }])
    setThinking(true)
    let ans
    try {
      ans = await askQuestion(
        { question: q, profile, config },
        (e) => setThinkStage(e),
      )
      setMessages((m) => [...m, { role: 'assistant', data: ans }])
    } catch (err) {
      ans = { refused: false, error: err.message }
      setMessages((m) => [...m, { role: 'assistant', data: ans }])
    } finally {
      setThinking(false)
      setThinkStage(null)
    }
    addHistoryRecord({ question: q, profile, config, answer: ans })
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="consult-page">
      {/* 左：个案上下文 */}
      <aside className="case-panel">
        <h2 className="panel-title">个案上下文</h2>

        {!profile ? (
          <>
            <div className="report-upload" onClick={() => fileRef.current?.click()}>
              <div className="ru-icon">📋</div>
              <div className="ru-text">上传孩子的成长报告</div>
              <div className="ru-hint">评估量表 / 行为描述 / 发育里程碑 · 仅用于本次会话，不入公共库</div>
              <div className="ru-hint">扫描版 PDF 可能无法自动解析，可改传 Word/txt 或手动填写</div>
              <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt" hidden
                onChange={(e) => { onPickReport(e.target.files[0]); e.target.value = '' }} />
            </div>
            <button className="btn btn-outline btn-block" type="button" onClick={startManualProfile}>
              跳过上传，手动填写个案信息
            </button>
          </>
        ) : (
          <div className="profile-card">
            <div className="pc-source">📋 {profile.sourceName || '手动填写'}</div>
            <label className="pc-field">年龄
              <input value={profile.age} onChange={(e) => updateProfile({ age: e.target.value })} placeholder="如 3 岁 6 个月" />
            </label>
            <label className="pc-field">核心表现（顿号分隔）
              <textarea rows={2} value={profile.coreSymptoms.join('、')}
                onChange={(e) => updateProfile({ coreSymptoms: e.target.value.split(/[、,，]/).map((s) => s.trim()).filter(Boolean) })} />
            </label>
            <label className="pc-field">既往评估（顿号分隔）
              <textarea rows={2} value={profile.assessments.join('、')}
                onChange={(e) => updateProfile({ assessments: e.target.value.split(/[、,，]/).map((s) => s.trim()).filter(Boolean) })} />
            </label>
            {profile.note && <p className="pc-note">{profile.note}</p>}
          </div>
        )}

        {extracting && <div className="extracting">⏳ {extractStage}</div>}

        <div className="case-config">
          <label>模型
            <select value={model} onChange={(e) => setModel(e.target.value)}>
              {MODELS.map((m) => <option key={m}>{m}</option>)}
            </select>
          </label>
          <label>检索 Top-K：<b>{topK}</b>
            <input type="range" min="1" max="10" value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
          </label>
          <label className="web-search-toggle">
            <input
              type="checkbox"
              checked={enableWebSearch}
              onChange={(e) => setEnableWebSearch(e.target.checked)}
            />
            启用网络补充检索
            <span className="web-search-hint">默认关 · 网络来源仅供参考，文献仍是主依据</span>
          </label>
        </div>

        <button className="btn btn-outline btn-block" onClick={clearSession}>清空会话</button>
      </aside>

      {/* 右：对话区 */}
      <section className="chat-panel">
        <div className="chat-scroll">
          {messages.length === 0 && !thinking && (
            <div className="chat-empty">
              <div className="ce-icon">💬</div>
              <h3>开始咨询</h3>
              <p>可先上传成长报告以获得更贴合孩子的建议，也可直接提问。<br />例如：「孩子 3 岁不进行眼神交流、无语言，家庭可以做哪些早期干预？」</p>
              <p className="ce-warn">⚠ 涉及用药、剂量、急症、确诊等问题，系统将拒答并建议线下就医。</p>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div className="msg msg-user" key={i}><div className="bubble">{m.text}</div></div>
            ) : (
              <div className="msg msg-bot" key={i}>
                <div className="bubble bubble-bot"><ConsultAnswer data={m.data} /></div>
              </div>
            ),
          )}

          {thinking && (
            <div className="msg msg-bot">
              <div className="bubble bubble-bot thinking">
                <span className="spinner" />
                {thinkStage ? `${thinkStage.stage}：${thinkStage.detail}` : '处理中…'}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="chat-input">
          <textarea
            value={input}
            placeholder="描述孩子的情况并提问…（Enter 发送，Shift+Enter 换行）"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
          />
          <button className="btn btn-primary" onClick={send} disabled={!input.trim() || thinking}>发送</button>
        </div>
      </section>
    </div>
  )
}
