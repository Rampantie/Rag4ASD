import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStats } from '../api/literature.js'

const STEPS = [
  { n: '1', title: '上传权威文献', desc: '导入指南、同行评议文献等，系统切分、向量化构建知识库。', icon: '📚' },
  { n: '2', title: '提供孩子情况并提问', desc: '上传成长报告并描述问题，报告仅用于本次会话、不入公共库。', icon: '🧩' },
  { n: '3', title: '获得带出处的建议', desc: '基于文献给出循证建议方向，每条标注来源，可点开原文核对。', icon: '🔎' },
]

const ACK_KEY = 'asd_disclaimer_acknowledged'

export default function Home() {
  const navigate = useNavigate()
  const [acked, setAcked] = useState(true)
  const [docCount, setDocCount] = useState(0)

  useEffect(() => {
    setAcked(localStorage.getItem(ACK_KEY) === '1')
    getStats()
      .then((s) => setDocCount(s.docCount))
      .catch(() => setDocCount(0))
  }, [])

  const acknowledge = () => {
    localStorage.setItem(ACK_KEY, '1')
    setAcked(true)
  }

  return (
    <div className="home">
      {/* 首次访问的免责告知（合规设计） */}
      {!acked && (
        <div className="modal-mask">
          <div className="modal">
            <h2>使用前请知悉</h2>
            <p>
              「星语」基于您上传的权威文献提供孤独症早期干预的<strong>循证信息参考</strong>，
              旨在帮助家长 / 教师理解干预方向。
            </p>
            <ul>
              <li>本系统<strong>不是诊断工具</strong>，输出<strong>不替代</strong>专业医师、治疗师或特教评估。</li>
              <li>涉及用药、剂量、急症、确诊等高风险问题，系统将拒绝直接结论并建议线下就医。</li>
              <li>孩子的成长报告仅用于当前咨询会话，不写入公共知识库。</li>
            </ul>
            <button className="btn btn-primary btn-block" onClick={acknowledge}>
              我已知悉，继续使用
            </button>
          </div>
        </div>
      )}

      {/* Hero */}
      <section className="hero">
        <h1>
          让每一条干预建议，<br />都有<span className="accent">权威来源</span>可循
        </h1>
        <p className="hero-sub">
          面向孤独症（ASD）儿童家长与早期干预人员的循证问答助手 ——
          上传权威文献构建知识库，结合孩子的成长情况，获得可溯源的干预建议方向。
        </p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={() => navigate('/consult')}>开始咨询 →</button>
          <button className="btn btn-ghost" onClick={() => navigate('/literature')}>去管理文献</button>
        </div>
      </section>

      {/* 醒目免责卡片 */}
      <section className="disclaimer-card">
        <span className="disclaimer-icon">⚠</span>
        <div>
          <strong>重要提示</strong>
          <p>
            本系统提供的是基于文献的信息参考，<strong>不构成医疗诊断或治疗方案</strong>，
            不替代专业医师、治疗师与特殊教育评估。请务必结合专业意见，必要时及时线下就医。
          </p>
        </div>
      </section>

      {/* 三步引导 */}
      <section className="steps-section">
        <h2 className="section-title">三步获得带出处的建议</h2>
        <div className="steps">
          {STEPS.map((s) => (
            <div className="step-card" key={s.n}>
              <div className="step-head">
                <span className="step-icon">{s.icon}</span>
                <span className="step-no">STEP {s.n}</span>
              </div>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 知识库状态 */}
      <section className="status-section">
        <div className="status-card">
          <div className="status-num">{docCount}</div>
          <div className="status-label">
            篇文献已入库
            <span className="status-hint">（来自知识库实时统计）</span>
          </div>
          <button className="btn btn-outline" onClick={() => navigate('/literature')}>
            {docCount === 0 ? '先去上传文献' : '管理知识库'}
          </button>
        </div>
      </section>
    </div>
  )
}
