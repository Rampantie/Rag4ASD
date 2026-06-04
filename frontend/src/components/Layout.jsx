import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: '首页', end: true },
  { to: '/literature', label: '文献知识库' },
  { to: '/consult', label: '个案咨询' },
  { to: '/history', label: '咨询历史' },
  { to: '/experiment', label: '实验对比' },
]

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-logo" aria-hidden>✦</span>
          <div className="brand-text">
            <strong>星语</strong>
            <span className="brand-sub">孤独症儿童干预建议问答</span>
          </div>
        </div>
        <nav className="app-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="header-status" title="当前模型（演示占位）">
          <span className="dot" /> DeepSeek · Top-K 4
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        ⚠ 本系统为辅助信息参考工具，<strong>不构成医疗诊断，不替代专业医师 / 治疗师 / 特教评估</strong>。所有建议均标注文献出处，请结合专业意见使用。
      </footer>
    </div>
  )
}
