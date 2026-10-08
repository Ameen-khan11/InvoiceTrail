import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiFetch } from '../api';

export default function InvoiceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Record payment modal state
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const [paymentData, setPaymentData] = useState({
    amount: '',
    paid_on: new Date().toISOString().split('T')[0],
    method: 'bank',
    reference: '',
  });

  // Remind button cooldown
  const [reminderLoading, setReminderLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);

  const handleDownloadPdf = async () => {
    try {
      setPdfDownloading(true);
      const blob = await apiFetch(`/invoices/${id}/pdf`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice-${invoice.invoice_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF: ' + err.message);
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleCopyPublicLink = () => {
    if (!invoice?.public_token) return;
    const publicUrl = `${window.location.origin}/public/invoice/${invoice.public_token}`;
    navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const loadInvoice = async () => {
    try {
      const data = await apiFetch(`/invoices/${id}`);
      setInvoice(data);
      // Pre-fill payment amount with remaining balance
      setPaymentData((prev) => ({
        ...prev,
        amount: data.balance_due,
      }));
    } catch (err) {
      setError(err.message || 'Invoice not found');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInvoice();
  }, [id]);

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    setPaymentError('');
    setPaymentLoading(true);

    try {
      await apiFetch(`/invoices/${id}/payments`, {
        method: 'POST',
        body: JSON.stringify(paymentData),
      });
      setShowPaymentModal(false);
      setActionSuccess('Payment recorded successfully!');
      loadInvoice();
    } catch (err) {
      setPaymentError(err.message || 'Failed to record payment');
    } finally {
      setPaymentLoading(false);
    }
  };

  const handleDeletePayment = async (paymentId) => {
    if (!window.confirm('Are you sure you want to delete this payment? The invoice status will be recalculated.')) {
      return;
    }

    try {
      await apiFetch(`/payments/${paymentId}`, {
        method: 'DELETE',
      });
      setActionSuccess('Payment deleted and invoice balance recalculated.');
      loadInvoice();
    } catch (err) {
      alert('Failed to delete payment: ' + err.message);
    }
  };

  const handleSendReminder = async () => {
    setReminderLoading(true);
    setActionSuccess('');
    setError('');

    try {
      const res = await apiFetch(`/invoices/${id}/remind`, {
        method: 'POST',
      });
      setActionSuccess(res.message || 'Reminder email dispatched to client.');
      loadInvoice();
    } catch (err) {
      setError(err.message || 'Failed to send reminder email');
    } finally {
      setReminderLoading(false);
    }
  };

  const handleDeleteInvoice = async () => {
    if (!window.confirm(`Are you sure you want to delete Invoice #${invoice?.invoice_number}? Note: This deletes this specific invoice, NOT the client.`)) {
      return;
    }

    try {
      await apiFetch(`/invoices/${id}`, {
        method: 'DELETE',
      });
      navigate('/invoices');
    } catch (err) {
      alert('Failed to delete invoice: ' + err.message);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading invoice details...</div>;
  }

  if (error && !invoice) {
    return (
      <div className="empty-state">
        <div className="empty-state-title">{error}</div>
        <Link to="/invoices" className="btn btn-primary" style={{ marginTop: '1rem' }}>
          Back to Invoices
        </Link>
      </div>
    );
  }

  // Check 24-hour reminder rate limit
  const isReminderOnCooldown = () => {
    if (!invoice?.last_reminder_sent_at) return false;
    const lastSent = new Date(invoice.last_reminder_sent_at);
    const now = new Date();
    const diffHours = (now - lastSent) / (1000 * 60 * 60);
    return diffHours < 24;
  };

  const onCooldown = isReminderOnCooldown();

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/invoices" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: '0.9rem' }}>
          ← Back to Invoices
        </Link>
      </div>

      {actionSuccess && <div className="alert alert-success">{actionSuccess}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Invoice Header */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: 0 }}>{invoice.invoice_number}</h1>
            <span className={`badge badge-${invoice.status}`}>{invoice.status.replace('_', ' ')}</span>
            {invoice.is_overdue && (
              <span className="badge badge-overdue">Overdue ({invoice.days_late} days)</span>
            )}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Issued on <strong>{invoice.issue_date}</strong> • Due on <strong>{invoice.due_date}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            onClick={handleDownloadPdf}
            disabled={pdfDownloading}
            className="btn btn-secondary"
            title="Download printable PDF invoice"
          >
            {pdfDownloading ? 'Generating PDF...' : 'Download PDF'}
          </button>

          {invoice?.public_token && (
            <button
              onClick={handleCopyPublicLink}
              className="btn btn-secondary"
              title="Copy client-accessible public link to clipboard"
            >
              {copied ? 'Link Copied' : 'Share Link'}
            </button>
          )}

          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
            <>
              <button
                onClick={handleSendReminder}
                disabled={reminderLoading || onCooldown}
                className="btn btn-secondary"
                title={onCooldown ? 'Reminder cooldown active (max 1 per 24 hours)' : 'Send polite reminder email to client'}
              >
                {reminderLoading ? 'Sending...' : onCooldown ? 'Reminded recently' : 'Send Reminder'}
              </button>

              <button onClick={() => setShowPaymentModal(true)} className="btn btn-primary">
                + Record Payment
              </button>
            </>
          )}

          <button onClick={handleDeleteInvoice} className="btn btn-danger btn-sm" title="Delete this invoice">
            Delete Invoice
          </button>
        </div>
      </div>

      {/* Financial Summary & Client Info */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Financial Cards */}
        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Financial Overview</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Invoice Total:</span>
              <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>
                {invoice.currency} {invoice.amount}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Total Paid:</span>
              <span style={{ color: 'var(--success)', fontWeight: 700 }}>
                {invoice.currency} {invoice.total_paid}
              </span>
            </div>
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 600 }}>Balance Due:</span>
              <span style={{ color: parseFloat(invoice.balance_due) > 0 ? 'var(--danger)' : 'var(--text-main)', fontWeight: 800, fontSize: '1.25rem' }}>
                {invoice.currency} {invoice.balance_due}
              </span>
            </div>
          </div>
        </div>

        {/* Client Card */}
        <div className="card">
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>Client Details</h2>
          {invoice.client ? (
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{invoice.client.name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
                {invoice.client.email}
              </div>
              <div style={{ marginTop: '0.75rem' }}>
                <Link to={`/clients`} style={{ fontSize: '0.85rem', color: 'var(--primary)', textDecoration: 'none' }}>
                  View client profile →
                </Link>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)' }}>No client information</div>
          )}

          {invoice.last_reminder_sent_at && (
            <div style={{ marginTop: '1rem', padding: '0.5rem', background: '#f8fafc', borderRadius: 4, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Last reminder email sent: {new Date(invoice.last_reminder_sent_at).toLocaleString()}
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      {invoice.description && (
        <div className="card">
          <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem' }}>Scope / Description</h2>
          <p style={{ whiteSpace: 'pre-wrap', color: 'var(--text-muted)', fontSize: '0.95rem' }}>
            {invoice.description}
          </p>
        </div>
      )}

      {/* Payment History */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Payment History</h2>
          {invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
            <button onClick={() => setShowPaymentModal(true)} className="btn btn-outline btn-sm">
              + Add Payment
            </button>
          )}
        </div>

        {invoice.payments?.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            No payments recorded yet for this invoice.
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Paid On</th>
                  <th>Amount</th>
                  <th>Method</th>
                  <th>Reference</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {invoice.payments.map((p) => (
                  <tr key={p.id}>
                    <td>{p.paid_on}</td>
                    <td style={{ fontWeight: 700, color: 'var(--success)' }}>
                      {invoice.currency} {p.amount}
                    </td>
                    <td>
                      <span className="badge badge-sent">{p.method}</span>
                    </td>
                    <td>{p.reference || '—'}</td>
                    <td>
                      <button
                        onClick={() => handleDeletePayment(p.id)}
                        className="btn btn-outline btn-sm"
                        style={{ color: 'var(--danger)' }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Record Payment Modal */}
      {showPaymentModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Record Payment</h2>
              <button onClick={() => setShowPaymentModal(false)} className="modal-close">
                &times;
              </button>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Remaining balance: <strong>{invoice.currency} {invoice.balance_due}</strong>
            </p>

            {paymentError && <div className="alert alert-error">{paymentError}</div>}

            <form onSubmit={handleRecordPayment}>
              <div className="form-group">
                <label className="form-label">Payment Amount *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={invoice.balance_due}
                  required
                  className="form-input"
                  value={paymentData.amount}
                  onChange={(e) => setPaymentData({ ...paymentData, amount: e.target.value })}
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Paid On *</label>
                  <input
                    type="date"
                    required
                    className="form-input"
                    value={paymentData.paid_on}
                    onChange={(e) => setPaymentData({ ...paymentData, paid_on: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Method *</label>
                  <select
                    className="form-select"
                    value={paymentData.method}
                    onChange={(e) => setPaymentData({ ...paymentData, method: e.target.value })}
                  >
                    <option value="bank">Bank Transfer (IBFT / Raast)</option>
                    <option value="upi">QR / EasyPaisa / JazzCash</option>
                    <option value="cash">Cash</option>
                    <option value="card">Card / POS</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Payment Reference / Note</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Transaction ID, UTR, Cheque #"
                  value={paymentData.reference}
                  onChange={(e) => setPaymentData({ ...paymentData, reference: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowPaymentModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={paymentLoading} className="btn btn-primary">
                  {paymentLoading ? 'Recording...' : 'Record Payment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
