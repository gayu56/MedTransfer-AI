import { Outlet, NavLink } from 'react-router-dom'
import { Activity, Users, Building2, ArrowRightLeft, Ambulance } from 'lucide-react'
import AgentChat from './AgentChat'

const navItems = [
  { to: '/dashboard', icon: Activity, label: 'Dashboard' },
  { to: '/dashboard/patients', icon: Users, label: 'Patients' },
  { to: '/dashboard/transfers/new', icon: ArrowRightLeft, label: 'New Transfer' },
  { to: '/dashboard/facilities', icon: Building2, label: 'Facilities' },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white/80 backdrop-blur-xl border-r border-slate-200/80 flex flex-col">
        <div className="p-5 border-b border-slate-200/70">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center shadow-sm shadow-primary-600/30">
              <Ambulance className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 tracking-tight">MedTransfer<span className="text-primary-600">AI</span></h1>
              <p className="text-[10px] text-slate-500">Patient Transfer Coordinator</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/dashboard'}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-primary-50 to-primary-100/40 text-primary-700 shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full bg-primary-600" />}
                  <Icon className={`w-4 h-4 transition-transform duration-200 ${isActive ? 'text-primary-600' : 'group-hover:scale-110'}`} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200/70">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center text-primary-700 text-xs font-bold ring-2 ring-white shadow-sm">SJ</div>
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
