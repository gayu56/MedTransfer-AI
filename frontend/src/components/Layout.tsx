import { Outlet, NavLink } from 'react-router-dom'
import { Activity, Users, Building2, ArrowRightLeft } from 'lucide-react'
import AgentChat from './AgentChat'

const navItems = [
  { to: '/', icon: Activity, label: 'Dashboard' },
  { to: '/patients', icon: Users, label: 'Patients' },
  { to: '/transfers/new', icon: ArrowRightLeft, label: 'New Transfer' },
  { to: '/facilities', icon: Building2, label: 'Facilities' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-5 border-b border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <ArrowRightLeft className="w-4 h-4 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900">IPTC</h1>
              <p className="text-[10px] text-slate-500">Patient Transfer Coordinator</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 text-xs font-bold">SJ</div>
            <div>
              <p className="text-sm font-medium text-slate-900">Sarah Johnson, NP</p>
              <p className="text-xs text-slate-500">Urgent Care East</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {/* AI Agent Chat */}
      <AgentChat />
    </div>
  )
}
