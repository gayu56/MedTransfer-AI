import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Patients from './pages/Patients'
import NewTransfer from './pages/NewTransfer'
import TransferDetail from './pages/TransferDetail'
import Facilities from './pages/Facilities'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="patients" element={<Patients />} />
        <Route path="transfers/new" element={<NewTransfer />} />
        <Route path="transfers/:id" element={<TransferDetail />} />
        <Route path="facilities" element={<Facilities />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
