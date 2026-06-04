import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import Literature from './pages/Literature.jsx'
import Placeholder from './pages/Placeholder.jsx'

// 路由对应 docs/页面与交互设计.md 的 5 个页面
// 目前仅首页(Home)完整实现，其余为占位页
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/literature" element={<Literature />} />
        <Route path="/consult" element={<Placeholder title="个案咨询" desc="上传成长报告 + 提问 → 带出处的干预建议（核心页面）" />} />
        <Route path="/history" element={<Placeholder title="咨询历史" desc="回溯过往会话与问答记录" />} />
        <Route path="/experiment" element={<Placeholder title="实验对比面板" desc="切换模型 / Top-K 跑对比，产出汇报证据" />} />
      </Route>
    </Routes>
  )
}
