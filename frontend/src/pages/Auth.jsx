import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiFetch } from '../api';

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.616z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
      <path d="M3.964 10.707c-.18-.54-.282-1.117-.282-1.707 0-.59.102-1.167.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  );
}

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Demo Google Sign-In state when VITE_GOOGLE_CLIENT_ID is not configured
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoEmail, setDemoEmail] = useState('google.user@example.com');
  const [demoName, setDemoName] = useState('Google User');

  const { login } = useAuth();
  const navigate = useNavigate();

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  // Initialize Google Identity Services if client ID is configured
  useEffect(() => {
    if (!googleClientId) return;

    const handleCredentialResponse = async (response) => {
      if (!response.credential) return;
      setError('');
      setGoogleLoading(true);
      try {
        const res = await apiFetch('/auth/google', {
          method: 'POST',
          body: JSON.stringify({ credential: response.credential }),
        });
        login(res.access_token, res.user);
        navigate('/');
      } catch (err) {
        setError(err.message || 'Google authentication failed');
      } finally {
        setGoogleLoading(false);
      }
    };

    if (!window.google) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        if (window.google?.accounts?.id) {
          window.google.accounts.id.initialize({
            client_id: googleClientId,
            callback: handleCredentialResponse,
          });
        }
      };
      document.body.appendChild(script);
    } else if (window.google?.accounts?.id) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleCredentialResponse,
      });
    }
  }, [googleClientId, login, navigate]);

  const handleGoogleClick = () => {
    setError('');
    if (googleClientId && window.google?.accounts?.id) {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          setShowDemoModal(true);
        }
      });
    } else {
      setShowDemoModal(true);
    }
  };

  const handleDemoGoogleAuth = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setGoogleLoading(true);
    setShowDemoModal(false);

    try {
      const res = await apiFetch('/auth/google', {
        method: 'POST',
        body: JSON.stringify({
          demo_email: demoEmail,
          demo_name: demoName,
        }),
      });
      login(res.access_token, res.user);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Google authentication failed');
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        const res = await apiFetch('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        login(res.access_token, res.user);
        navigate('/');
      } else {
        const res = await apiFetch('/auth/signup', {
          method: 'POST',
          body: JSON.stringify({
            name,
            email,
            password,
            business_name: businessName,
          }),
        });
        login(res.access_token, res.user);
        navigate('/');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', padding: '1rem' }}>
      <div style={{ maxWidth: 460, width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--primary)', marginBottom: '0.5rem' }}>
            InvoiceTrail
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>
            {isLogin ? 'Log in to track your invoices and payments' : 'Create your free invoice tracker account'}
          </p>
        </div>

        <div className="card" style={{ padding: '2rem', boxShadow: 'var(--shadow-lg)' }}>
          {error && <div className="alert alert-error">{error}</div>}

          {/* Continue with Google Button */}
          <button
            type="button"
            onClick={handleGoogleClick}
            disabled={googleLoading || loading}
            className="btn-google"
          >
            <GoogleIcon />
            <span>{googleLoading ? 'Connecting to Google...' : 'Continue with Google'}</span>
          </button>

          {/* Divider */}
          <div className="auth-divider">
            <span>or continue with email</span>
          </div>

          <form onSubmit={handleSubmit}>
            {!isLogin && (
              <>
                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. John Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Business / Agency Name (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. My Studio"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                  />
                </div>
              </>
            )}

            <div className="form-group">
              <label className="form-label">Email Address *</label>
              <input
                type="email"
                required
                className="form-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Password * {isLogin ? '' : '(min 8 chars)'}</label>
              <input
                type="password"
                required
                minLength={isLogin ? 1 : 8}
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem', padding: '0.85rem', fontSize: '1rem' }}
            >
              {loading ? 'Please wait...' : isLogin ? 'Log In' : 'Create Free Account'}
            </button>
          </form>

          <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.95rem', color: 'var(--text-muted)' }}>
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--primary)',
                fontWeight: 600,
                cursor: 'pointer',
                textDecoration: 'none',
                padding: '0 0.25rem',
              }}
            >
              {isLogin ? 'Sign up' : 'Log in'}
            </button>
          </div>
        </div>
      </div>

      {/* Google Dev / Demo Modal */}
      {showDemoModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: 440 }}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <GoogleIcon />
                <h3 className="modal-title" style={{ fontSize: '1.15rem' }}>Google Sign-In</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowDemoModal(false)}
                className="modal-close"
              >
                &times;
              </button>
            </div>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
              {googleClientId
                ? 'Google popup was closed or blocked. You can test sign-in directly below:'
                : 'Google OAuth Client ID is not yet set in .env. Test Google Sign-In directly in development mode:'}
            </p>

            <form onSubmit={handleDemoGoogleAuth}>
              <div className="form-group">
                <label className="form-label">Google Account Name</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  value={demoName}
                  onChange={(e) => setDemoName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Google Account Email</label>
                <input
                  type="email"
                  required
                  className="form-input"
                  value={demoEmail}
                  onChange={(e) => setDemoEmail(e.target.value)}
                />
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  Use any email or test linking with an existing account.
                </div>
              </div>

              <div className="modal-actions" style={{ marginTop: '1.25rem' }}>
                <button
                  type="button"
                  onClick={() => setShowDemoModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={googleLoading}
                  className="btn btn-primary"
                >
                  {googleLoading ? 'Signing In...' : 'Sign In with Google'}
                </button>
              </div>
            </form>

            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Tip: In production, add your real Google OAuth Client ID to <code>frontend/.env</code> as <code>VITE_GOOGLE_CLIENT_ID</code>.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
