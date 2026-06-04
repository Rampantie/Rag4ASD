import { useNavigate } from 'react-router-dom'

// 通用占位页：除首页外的页面尚未实现
export default function Placeholder({ title, desc }) {
  const navigate = useNavigate()
  return (
    <div className="placeholder">
      <div className="placeholder-badge">开发中</div>
      <h1>{title}</h1>
      <p>{desc}</p>
      <p className="placeholder-note">该页面将在后续里程碑中实现，当前先展示首页效果。</p>
      <button className="btn btn-ghost" onClick={() => navigate('/')}>← 返回首页</button>
    </div>
  )
}
