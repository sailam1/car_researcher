import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ResearchPage } from './pages/ResearchPage'
import { ComparePage } from './pages/ComparePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ResearchPage />} />
        <Route path="/compare" element={<ComparePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
