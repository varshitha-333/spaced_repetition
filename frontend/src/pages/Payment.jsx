import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { redeemPremium, getPremiumStatus } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import Navbar from '../components/Navbar';

const VALID_COUPONS = ['LAUNCH30', 'STUDENT30', 'FIRST100', 'LEARNFREE'];

export default function Payment() {
  const { user, refreshUser } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    name: user?.username || '',
    email: '',
    phone: '',
    coupon: 'LAUNCH30',
    card: '4242 4242 4242 4242',
    cvv: '123',
    expiry: '12/29',
  });
  const [loading, setLoading] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [alreadyPremium, setAlreadyPremium] = useState(null);

  useEffect(() => {
    getPremiumStatus().then(r => {
      if (r.data?.is_premium) setAlreadyPremium(r.data);
    }).catch(() => {});
  }, []);

  const upper = form.coupon.toUpperCase();
  const couponValid = VALID_COUPONS.includes(upper);
  const finalPrice = couponValid ? 0 : 499;

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handlePay = async (e) => {
    e.preventDefault();
    if (!couponValid) {
      toast.error('Coupon not recognised. Try LAUNCH30, STUDENT30, FIRST100, or LEARNFREE.');
      return;
    }
    if (!form.name || !form.email) {
      toast.error('Please fill name and email');
      return;
    }
    setLoading(true);
    try {
      const r = await redeemPremium({
        name: form.name, email: form.email, phone: form.phone, coupon: upper,
      });
      setReceipt(r.data.receipt);
      await refreshUser();
      toast.success('🎉 Premium activated for 30 days!');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  if (alreadyPremium) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-16">
          <div className="card p-10 text-center">
            <div className="text-5xl mb-4">✨</div>
            <h1 className="font-display text-3xl font-bold mb-2">You're already on Premium</h1>
            <p className="text-ink-muted mb-4">
              {alreadyPremium.days_left} day{alreadyPremium.days_left !== 1 && 's'} left ·
              expires {new Date(alreadyPremium.expires_at).toLocaleDateString()}
            </p>
            <div className="flex justify-center gap-3">
              <Link to="/premium" className="btn-primary">Try AI features →</Link>
              <Link to="/dashboard" className="btn-secondary">Back to dashboard</Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-10">
        <AnimatePresence mode="wait">
          {!receipt ? (
            <motion.div
              key="form"
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="grid md:grid-cols-5 gap-6"
            >
              {/* Form */}
              <form onSubmit={handlePay} className="card p-7 md:col-span-3">
                <div className="pill-peach mb-4">🎁 30-day launch offer</div>
                <h1 className="font-display text-2xl font-bold mb-1">Activate Premium</h1>
                <p className="text-sm text-ink-muted mb-6">
                  This is a demo checkout. Your card is not actually charged — coupon makes it ₹0.
                </p>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <div className="label mb-1">Full name</div>
                    <input className="input" required value={form.name} onChange={e => set('name', e.target.value)} />
                  </div>
                  <div>
                    <div className="label mb-1">Email</div>
                    <input type="email" className="input" required value={form.email} onChange={e => set('email', e.target.value)} placeholder="you@college.edu" />
                  </div>
                  <div className="sm:col-span-2">
                    <div className="label mb-1">Phone (for SMS reminders, optional)</div>
                    <input className="input" value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="+91 …" />
                  </div>
                </div>

                <div className="mt-6">
                  <div className="label mb-1">Coupon code</div>
                  <div className="flex gap-2">
                    <input
                      className={`input flex-1 uppercase font-mono tracking-wider ${couponValid ? 'border-emerald-400' : ''}`}
                      value={form.coupon}
                      onChange={e => set('coupon', e.target.value.toUpperCase())}
                    />
                    {couponValid && <div className="pill-sage self-center">−₹499</div>}
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {VALID_COUPONS.map(c => (
                      <button
                        type="button"
                        key={c}
                        onClick={() => set('coupon', c)}
                        className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded hover:bg-indigo-100"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-6 grid sm:grid-cols-3 gap-4 opacity-60">
                  <div className="sm:col-span-3">
                    <div className="label mb-1">Card number (demo — pre-filled)</div>
                    <input className="input font-mono" value={form.card} onChange={e => set('card', e.target.value)} />
                  </div>
                  <div>
                    <div className="label mb-1">Expiry</div>
                    <input className="input font-mono" value={form.expiry} onChange={e => set('expiry', e.target.value)} />
                  </div>
                  <div>
                    <div className="label mb-1">CVV</div>
                    <input className="input font-mono" value={form.cvv} onChange={e => set('cvv', e.target.value)} />
                  </div>
                </div>

                <button type="submit" disabled={loading} className="btn-peach w-full mt-7 !py-3 text-base">
                  {loading ? 'Processing…' : `Pay ₹${finalPrice} & unlock Premium`}
                </button>
                <div className="text-xs text-ink-muted text-center mt-3">
                  By continuing you agree this is a demo checkout for the launch campaign.
                </div>
              </form>

              {/* Summary */}
              <div className="md:col-span-2">
                <div className="card p-6 sticky top-24">
                  <div className="font-semibold mb-4">Order summary</div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-ink-muted">Premium · 30 days</span>
                    <span>₹499</span>
                  </div>
                  {couponValid && (
                    <div className="flex justify-between text-sm mb-2 text-emerald-700">
                      <span>Coupon {upper}</span>
                      <span>− ₹499</span>
                    </div>
                  )}
                  <div className="border-t border-indigo-100 mt-3 pt-3 flex justify-between font-bold text-lg">
                    <span>Total</span>
                    <span>₹{finalPrice}</span>
                  </div>
                  <div className="mt-5 text-xs text-ink-muted leading-relaxed">
                    You'll get full Premium access for 30 days. After that, you'll automatically move to Free —
                    we never auto-charge.
                  </div>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="receipt"
              initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
              className="card p-10 text-center max-w-xl mx-auto"
            >
              <div className="text-6xl mb-3 animate-pop">🎉</div>
              <h1 className="font-display text-3xl font-bold mb-2">Premium activated!</h1>
              <p className="text-ink-muted mb-6">
                You have full access for 30 days. Expires on{' '}
                <span className="font-semibold text-ink">
                  {new Date(receipt.expires_at).toLocaleDateString(undefined, { dateStyle: 'long' })}
                </span>.
              </p>

              <div className="card-quiet p-5 text-left text-sm font-mono mb-6">
                <div className="flex justify-between"><span>Receipt</span><span>{receipt.id}</span></div>
                <div className="flex justify-between"><span>Coupon</span><span>{receipt.coupon}</span></div>
                <div className="flex justify-between"><span>Name</span><span>{receipt.name}</span></div>
                <div className="flex justify-between"><span>Email</span><span>{receipt.email}</span></div>
                <div className="flex justify-between border-t border-indigo-100 mt-2 pt-2"><span>Total paid</span><span>₹0</span></div>
              </div>

              <div className="flex justify-center gap-3">
                <button onClick={() => nav('/premium')} className="btn-primary">Open AI Lab →</button>
                <button onClick={() => nav('/dashboard')} className="btn-secondary">Back to dashboard</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
