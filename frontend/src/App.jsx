import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Home from './pages/Home.jsx'
import Literature from './pages/Literature.jsx'
import Consult from './pages/Consult.jsx'
import History from './pages/History.jsx'
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/literature" element={<Literature />} />
        <Route path="/consult" element={<Consult />} />
        <Route path="/history" element={<History />} />
      </Route>
    </Routes>
  )
}
