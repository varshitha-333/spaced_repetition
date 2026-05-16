import { Link } from 'react-router-dom';

export default function PremiumBadge({ premium }) {
  if (!premium) return null;
  if (!premium.is_premium) {
    return (
      <Link to="/pricing" className="pill bg-peach-100 text-peach-600 hover:bg-peach-200 transition">
        🎁 Premium FREE 30 days
      </Link>
    );
  }
  return (
    <Link to="/profile" className="pill premium-ribbon text-white hover:opacity-95">
      ✨ Premium · {premium.days_left}d left
    </Link>
  );
}
