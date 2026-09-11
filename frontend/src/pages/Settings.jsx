import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import { useAuth } from '../context/AuthContext';

export default function Settings() {
  const { setUser: setAuthUser } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    business_name: '',
    email_reminders_enabled: true,
  });

  const loadSettings = async () => {
    try {
      const res = await apiFetch('/settings');
      setSettings(res);
      setFormData({
        name: res.user.name || '',
        business_name: res.user.business_name || '',
        email_reminders_enabled: res.user.email_reminders_enabled ?? true,
      });
    } catch (err) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const res = await apiFetch('/settings', {
        method: 'PUT',
        body: JSON.stringify(formData),
      });
      setSuccess(res.message || 'Settings saved successfully');
      setAuthUser(res.user);
      loadSettings();
    } catch (err) {
      setError(err.message || 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading settings...</div>;
  }

  const { user, usage } = settings || { user: {}, usage: {} };

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Account Settings</h1>
          <p className="page-subtitle">Manage your profile, email reminders, and view plan usage</p>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Plan & Usage Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Current Subscription</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {usage?.is_pro ? 'Professional plan with unlimited clients and invoices' : 'Free tier for solo freelancers'}
            </p>
          </div>
          <div>
            {usage?.is_pro ? (
              <span className="badge badge-pro" style={{ fontSize: '0.9rem', padding: '0.3rem 0.8rem' }}>
                PRO PLAN
              </span>
            ) : (
              <span className="brand-badge" style={{ fontSize: '0.85rem', padding: '0.3rem 0.8rem' }}>
                FREE PLAN
              </span>
            )}
          </div>
        </div>

        {/* Usage Progress Indicators */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 8, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              Clients Usage
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              {usage?.clients?.count} {usage?.is_pro ? 'clients' : `/ ${usage?.clients?.limit} clients`}
            </div>
            {usage?.clients?.at_limit && (
              <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                Reached free limit (5 clients)
              </div>
            )}
          </div>

          <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 8, border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
              Invoices Usage
            </div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              {usage?.invoices?.count} {usage?.is_pro ? 'invoices' : `/ ${usage?.invoices?.limit} invoices`}
            </div>
            {usage?.invoices?.at_limit && (
              <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                Reached free limit (20 invoices)
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Profile & Notification Form */}
      <div className="card">
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '1.25rem' }}>Profile & Notifications</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name *</label>
            <input
              type="text"
              required
              className="form-input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              disabled
              className="form-input"
              value={user?.email || ''}
              style={{ background: '#f1f5f9', cursor: 'not-allowed' }}
            />
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Email address cannot be changed once created.
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Business / Freelancer Brand Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. My Studio"
              value={formData.business_name}
              onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
            />
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Used as the sender name in client reminder emails.
            </div>
          </div>

          {/* Email Reminders Toggle */}
          <div className="form-group" style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem', marginTop: '1.25rem' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={formData.email_reminders_enabled}
                onChange={(e) => setFormData({ ...formData, email_reminders_enabled: e.target.checked })}
                style={{ marginTop: '0.25rem', width: 18, height: 18 }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                  Enable Daily 09:00 Overdue Invoice Digest
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  When enabled, you will receive a morning email listing any invoices that are overdue and need chasing. If no invoices are overdue, no email is sent.
                </div>
              </div>
            </label>
          </div>

          <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
