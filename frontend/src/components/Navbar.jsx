import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { getPremiumStatus } from '../services/api';
import PremiumBadge from './PremiumBadge';

const links = [
  { to: '/dashboard', label: 'Today' },
  { to: '/upload',    label: 'Add' },
  { to: '/upcoming',  label: 'Upcoming' },
  { to: '/premium',   label: 'AI Lab' },
  { to: '/history',   label: 'History' },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [premium, setPremium] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    getPremiumStatus().then(r => setPremium(r.data)).catch(() => {});
  }, [user, loc.pathname]);

  const handleLogout = async () => {
    await logout();
    nav('/');
  };

  return (
    <nav className="sticky top-0 z-40 backdrop-blur-xl bg-white/70 border-b border-white/60">
      <div className="container-page py-3 flex items-center gap-4">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white text-lg">
            📚
          </div>
          <span className="font-display font-bold text-lg text-ink">LearnFlow</span>
        </Link>

        <div className="hidden md:flex items-center gap-1 ml-4">
          {links.map(l => {
            const active = loc.pathname === l.to;
            return (
              <Link
                key={l.to}
                to={l.to}
                className={`px-3 py-1.5 rounded-lg text-sm transition ${
                  active
                    ? 'bg-indigo-100 text-indigo-700 font-semibold'
                    : 'text-ink-soft hover:bg-white hover:text-ink'
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </div>

        <div className="flex-1" />

        <PremiumBadge premium={premium} />

        <div className="hidden md:flex items-center gap-2">
          <Link to="/profile" className="btn-secondary !py-1.5 !px-3 text-sm">
            👤 {user?.username}
          </Link>
          <button onClick={handleLogout} className="btn-ghost !py-1.5 !px-3 text-sm">
            Logout
          </button>
        </div>

        <button
          onClick={() => setOpen(o => !o)}
          className="md:hidden btn-ghost !p-2"
          aria-label="Menu"
        >
          ☰
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-white/60 bg-white/90 backdrop-blur-xl animate-fade-in">
          <div className="container-page py-2 flex flex-col">
            {links.map(l => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className="py-2 text-sm text-ink-soft hover:text-ink"
              >
                {l.label}
              </Link>
            ))}
            <Link to="/profile" onClick={() => setOpen(false)} className="py-2 text-sm">👤 Profile</Link>
            <button onClick={handleLogout} className="py-2 text-sm text-left text-rose-600">Logout</button>
          </div>
        </div>
      )}
    </nav>
  );
}
