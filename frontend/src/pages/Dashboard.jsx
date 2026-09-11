import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [incomeData, setIncomeData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [sumRes, incRes] = await Promise.all([
          apiFetch('/dashboard/summary'),
          apiFetch('/dashboard/monthly-income'),
        ]);
        setSummary(sumRes);
        setIncomeData(incRes.monthly_income || []);
      } catch (err) {
        setError(err.message || 'Failed to load dashboard metrics');
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading dashboard metrics...</div>;
  }

  if (error) {
    return <div className="alert alert-error">{error}</div>;
  }

  const { cards, overdue_invoices } = summary || {
    cards: { total_outstanding: '0.00', overdue_amount: '0.00', paid_this_month: '0.00', counts_by_status: {} },
    overdue_invoices: [],
  };

  const hasAnyInvoices = Object.values(cards.counts_by_status || {}).some((c) => c > 0);

  // Maximum monthly income for chart scaling
  const maxIncome = Math.max(...incomeData.map((d) => parseFloat(d.income) || 0), 100);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Your real-time invoicing and payment collections summary</p>
        </div>
        <div>
          <Link to="/invoices" className="btn btn-primary">
            + New Invoice
          </Link>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Total Outstanding</div>
          <div className="metric-value">Rs.{cards.total_outstanding}</div>
          <div className="metric-sub">Uncollected sent & partial invoices</div>
        </div>

        <div className="metric-card">
          <div className="metric-label" style={{ color: parseFloat(cards.overdue_amount) > 0 ? 'var(--danger)' : undefined }}>
            Overdue Amount
          </div>
          <div className="metric-value" style={{ color: parseFloat(cards.overdue_amount) > 0 ? 'var(--danger)' : undefined }}>
            Rs.{cards.overdue_amount}
          </div>
          <div className="metric-sub">{cards.counts_by_status.overdue || 0} overdue invoices needing follow-up</div>
        </div>

        <div className="metric-card" style={{ borderLeftColor: 'var(--success)' }}>
          <div className="metric-label" style={{ color: 'var(--success)' }}>
            Paid This Month
          </div>
          <div className="metric-value" style={{ color: 'var(--success)' }}>
            Rs.{cards.paid_this_month}
          </div>
          <div className="metric-sub">Collections received this calendar month</div>
        </div>

        <div className="metric-card" style={{ borderLeftColor: 'var(--info)' }}>
          <div className="metric-label">Invoice Breakdown</div>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
            <span className="badge badge-draft">{cards.counts_by_status.draft || 0} draft</span>
            <span className="badge badge-sent">{cards.counts_by_status.sent || 0} sent</span>
            <span className="badge badge-partially_paid">{cards.counts_by_status.partially_paid || 0} partial</span>
            <span className="badge badge-paid">{cards.counts_by_status.paid || 0} paid</span>
          </div>
        </div>
      </div>

      {!hasAnyInvoices ? (
        <div className="empty-state">
          <div className="empty-state-title">No invoices recorded yet</div>
          <p className="empty-state-text">
            Add your clients and log your first invoice to start tracking payments and automated reminders.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <Link to="/clients" className="btn btn-secondary">
              Add First Client
            </Link>
            <Link to="/invoices" className="btn btn-primary">
              Create First Invoice
            </Link>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '1.5rem' }}>
          {/* Overdue Invoices Table */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Overdue Invoices</h2>
              <Link to="/invoices?status=overdue" className="btn btn-outline btn-sm">
                View All
              </Link>
            </div>

            {overdue_invoices.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                Great job! You have zero overdue invoices.
              </div>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Invoice</th>
                      <th>Client</th>
                      <th>Balance Due</th>
                      <th>Days Late</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overdue_invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td style={{ fontWeight: 600 }}>
                          <Link to={`/invoices/${inv.id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>
                            {inv.invoice_number}
                          </Link>
                        </td>
                        <td>{inv.client_name}</td>
                        <td style={{ fontWeight: 600 }}>Rs.{inv.balance_due}</td>
                        <td>
                          <span className="badge badge-overdue">{inv.days_late} days</span>
                        </td>
                        <td>
                          <Link to={`/invoices/${inv.id}`} className="btn btn-outline btn-sm">
                            Remind
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 6-Month Income Chart */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Monthly Collections (Last 6 Months)</h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Actual payments collected per month
            </p>

            <div className="chart-container">
              {incomeData.map((item, idx) => {
                const amount = parseFloat(item.income) || 0;
                const heightPercent = maxIncome > 0 ? (amount / maxIncome) * 100 : 0;
                return (
                  <div key={idx} className="chart-bar-group">
                    <div className="chart-amount">{amount > 0 ? `Rs.${amount}` : ''}</div>
                    <div
                      className="chart-bar"
                      style={{
                        height: `${Math.max(heightPercent, 4)}%`,
                        background: amount > 0 ? 'var(--primary)' : '#e2e8f0',
                      }}
                      title={`${item.month}: Rs.${item.income}`}
                    />
                    <div className="chart-label">{item.month}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
