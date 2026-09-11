import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { API_BASE } from '../api';

export default function PublicInvoice() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    async function fetchPublicInvoice() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/public/invoices/${token}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || 'Invoice not found or link has expired.');
        }
        const json = await res.json();
        setData(json);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      fetchPublicInvoice();
    }
  }, [token]);

  const handleDownloadPdf = async () => {
    try {
      setDownloading(true);
      const res = await fetch(`${API_BASE}/public/invoices/${token}/pdf`);
      if (!res.ok) throw new Error('Failed to generate PDF');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice-${data?.invoice?.invoice_number || 'download'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error downloading PDF: ' + err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 16px', width: '32px', height: '32px', border: '3px solid #e2e8f0', borderTopColor: '#0d9488', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          <p style={{ color: '#64748b' }}>Loading invoice...</p>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#f8fafc', padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
        <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '40px', maxWidth: '480px', width: '100%', textAlign: 'center', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
          <h2 style={{ color: '#0f172a', margin: '0 0 12px 0', fontSize: '1.5rem', fontWeight: '700' }}>Invoice Not Found</h2>
          <p style={{ color: '#64748b', fontSize: '15px', lineHeight: '1.6', margin: '0 0 32px 0' }}>
            {error || 'This invoice link is either expired or does not exist.'}
          </p>
          <a href="/" style={{ color: '#0d9488', textDecoration: 'none', fontWeight: '600', fontSize: '15px' }}>
            ← Back to InvoiceTrail
          </a>
        </div>
      </div>
    );
  }

  const { invoice, client, business, payments } = data;
  const isPaid = invoice.status === 'paid';
  const isOverdue = invoice.is_overdue;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f1f5f9', padding: '32px 16px', fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        {/* Top bar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <span style={{ fontSize: '20px', fontWeight: '700', color: '#0f172a' }}>InvoiceTrail</span>
            <span style={{ marginLeft: '12px', fontSize: '13px', fontWeight: '500', color: '#64748b', backgroundColor: '#e2e8f0', padding: '4px 10px', borderRadius: '16px' }}>Client Portal</span>
          </div>
          <button
            onClick={handleDownloadPdf}
            disabled={downloading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              backgroundColor: '#0f172a',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '10px 20px',
              fontWeight: '600',
              fontSize: '14px',
              cursor: downloading ? 'not-allowed' : 'pointer',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              transition: 'background-color 0.2s',
            }}
          >
            {downloading ? 'Preparing PDF...' : 'Download PDF'}
          </button>
        </div>

        {/* Invoice Paper Card */}
        <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '48px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01)', border: '1px solid #e2e8f0' }}>
          {/* Header Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '2px solid #f8fafc', paddingBottom: '32px', flexWrap: 'wrap', gap: '24px' }}>
            <div>
              <h1 style={{ margin: '0 0 8px 0', fontSize: '28px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.02em' }}>
                {business.name}
              </h1>
              <p style={{ margin: 0, color: '#64748b', fontSize: '15px' }}>{business.email}</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '32px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.03em' }}>
                INVOICE
              </div>
              <div style={{ fontSize: '16px', fontWeight: '600', color: '#64748b', marginTop: '4px' }}>
                #{invoice.invoice_number}
              </div>
              <div style={{ marginTop: '12px' }}>
                <span
                  style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    borderRadius: '9999px',
                    fontSize: '12px',
                    fontWeight: '700',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    backgroundColor: isPaid ? '#dcfce7' : isOverdue ? '#fee2e2' : invoice.status === 'partially_paid' ? '#fef3c7' : '#e0f2fe',
                    color: isPaid ? '#166534' : isOverdue ? '#991b1b' : invoice.status === 'partially_paid' ? '#92400e' : '#0369a1',
                  }}
                >
                  {isOverdue ? 'Overdue' : invoice.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>

          {/* Meta & Bill To */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px', margin: '32px 0', padding: '24px', backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px solid #f1f5f9' }}>
            <div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Billed To</span>
              <div style={{ fontSize: '16px', fontWeight: '700', color: '#0f172a', marginTop: '8px' }}>{client.name}</div>
              <div style={{ fontSize: '14px', color: '#64748b', marginTop: '4px' }}>{client.email}</div>
            </div>
            <div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Issue Date</span>
              <div style={{ fontSize: '15px', fontWeight: '600', color: '#334155', marginTop: '8px' }}>{invoice.issue_date}</div>
            </div>
            <div>
              <span style={{ fontSize: '12px', fontWeight: '700', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Due Date</span>
              <div style={{ fontSize: '15px', fontWeight: '700', color: isOverdue ? '#dc2626' : '#0f172a', marginTop: '8px' }}>
                {invoice.due_date} {isOverdue && <span style={{ fontWeight: '500', fontSize: '13px' }}><br/>({invoice.days_late}d overdue)</span>}
              </div>
            </div>
          </div>

          {/* Line Items Table */}
          <div style={{ marginBottom: '40px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
                  <th style={{ textAlign: 'left', padding: '12px 16px', fontSize: '13px', fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Description</th>
                  <th style={{ textAlign: 'right', padding: '12px 16px', fontSize: '13px', fontWeight: '700', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <td style={{ padding: '20px 16px', color: '#334155', fontSize: '15px', lineHeight: '1.5' }}>
                    {invoice.description || 'Professional Services'}
                  </td>
                  <td style={{ padding: '20px 16px', textAlign: 'right', fontWeight: '600', color: '#0f172a', fontSize: '16px' }}>
                    {invoice.currency} {parseFloat(invoice.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Payment History (if any) */}
          {payments && payments.length > 0 && (
            <div style={{ marginBottom: '40px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: '700', color: '#334155', margin: '0 0 16px 0' }}>Payment History</h3>
              <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ textAlign: 'left', padding: '12px 16px', color: '#64748b', fontWeight: '600' }}>Date</th>
                      <th style={{ textAlign: 'left', padding: '12px 16px', color: '#64748b', fontWeight: '600' }}>Note</th>
                      <th style={{ textAlign: 'right', padding: '12px 16px', color: '#64748b', fontWeight: '600' }}>Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((p, i) => (
                      <tr key={p.id} style={{ borderBottom: i === payments.length - 1 ? 'none' : '1px solid #f1f5f9' }}>
                        <td style={{ padding: '12px 16px', color: '#475569' }}>{p.paid_on}</td>
                        <td style={{ padding: '12px 16px', color: '#64748b' }}>
                          {p.reference ? `${p.method?.toUpperCase()} (${p.reference})` : (p.method?.toUpperCase() || 'Payment')}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right', color: '#16a34a', fontWeight: '600' }}>
                          -{invoice.currency} {parseFloat(p.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Summary / Total Due Box */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '32px' }}>
            <div style={{ width: '100%', maxWidth: '340px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: '15px', color: '#64748b' }}>
                <span>Total Amount:</span>
                <span style={{ fontWeight: '600', color: '#0f172a' }}>{invoice.currency} {parseFloat(invoice.amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: '15px', color: '#64748b' }}>
                <span>Total Paid:</span>
                <span style={{ fontWeight: '600', color: '#16a34a' }}>{invoice.currency} {parseFloat(invoice.total_paid).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '16px 0 0 0', marginTop: '12px', borderTop: '2px solid #e2e8f0', fontSize: '18px', fontWeight: '800' }}>
                <span style={{ color: '#0f172a' }}>Balance Due:</span>
                <span style={{ color: isPaid ? '#16a34a' : '#dc2626', fontSize: '20px' }}>
                  {invoice.currency} {parseFloat(invoice.balance_due).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>

          {/* Footer Note */}
          <div style={{ marginTop: '64px', paddingTop: '24px', borderTop: '1px solid #f1f5f9', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
            Questions regarding this invoice? Please email <a href={`mailto:${business.email}`} style={{ color: '#0d9488', textDecoration: 'none', fontWeight: '500' }}>{business.email}</a>.<br />
            <div style={{ marginTop: '8px' }}>Powered by InvoiceTrail</div>
          </div>
        </div>
      </div>
    </div>
  );
}
