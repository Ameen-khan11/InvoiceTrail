import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="app-layout">
      {/* Mobile Sidebar Overlay */}
      <div 
        className={`sidebar-overlay ${isSidebarOpen ? 'open' : ''}`} 
        onClick={closeSidebar}
      />

      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
        <NavLink to="/" className="sidebar-brand" onClick={closeSidebar}>
          InvoiceTrail
          {user?.is_pro ? (
            <span className="badge badge-pro">PRO</span>
          ) : (
            <span className="brand-badge">FREE</span>
          )}
        </NavLink>

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} onClick={closeSidebar}>
            Dashboard
          </NavLink>
          <NavLink to="/invoices" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} onClick={closeSidebar}>
            Invoices
          </NavLink>
          <NavLink to="/clients" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} onClick={closeSidebar}>
            Clients
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} onClick={closeSidebar}>
            Settings
          </NavLink>
        </nav>

        <div className="sidebar-user">
          <div style={{ fontSize: '0.9rem', color: '#cbd5e1', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.business_name || user?.name}
          </div>
          <button onClick={logout} className="btn btn-outline btn-sm" style={{ borderColor: '#334155', color: '#e2e8f0', width: '100%' }}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-content-area">
        <header className="mobile-header">
          <NavLink to="/" style={{ textDecoration: 'none', color: 'var(--text-main)', fontWeight: 700, fontSize: '1.25rem' }}>
            InvoiceTrail
          </NavLink>
          <button className="hamburger-btn" onClick={toggleSidebar}>
            ☰
          </button>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
