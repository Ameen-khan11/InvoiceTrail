import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiFetch } from '../api';

export default function Invoices() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [invoices, setInvoices] = useState([]);
  const [clients, setClients] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total_pages: 1, total_items: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filter state synced with URL params
  const search = searchParams.get('search') || '';
  const status = searchParams.get('status') || '';
  const clientId = searchParams.get('client_id') || '';
  const sort = searchParams.get('sort') || 'due_date';
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState('');
  const [formData, setFormData] = useState({
    invoice_number: '',
    client_id: '',
    issue_date: new Date().toISOString().split('T')[0],
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    amount: '',
    currency: 'PKR',
    description: '',
    status: 'draft',
  });

  const loadClients = async () => {
    try {
      const res = await apiFetch('/clients');
      setClients(res.clients || []);
      if (res.clients?.length > 0 && !formData.client_id) {
        setFormData((prev) => ({ ...prev, client_id: res.clients[0].id }));
      }
    } catch (err) {
      console.error('Failed to load clients list', err);
    }
  };

  const loadInvoices = async () => {
    setLoading(true);
    setError('');
    try {
      const query = new URLSearchParams({
        page: page.toString(),
        sort,
        ...(search ? { search } : {}),
        ...(status ? { status } : {}),
        ...(clientId ? { client_id: clientId } : {}),
      });

      const res = await apiFetch(`/invoices?${query.toString()}`);
      setInvoices(res.invoices || []);
      setPagination(res.pagination || { page: 1, total_pages: 1, total_items: 0 });
    } catch (err) {
      setError(err.message || 'Failed to fetch invoices');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    loadInvoices();
  }, [search, status, clientId, sort, page]);

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set('page', '1'); // Reset to page 1 on filter changes
    setSearchParams(next);
  };

  const handleExportCSV = async () => {
    try {
      const query = new URLSearchParams({
        sort,
        ...(search ? { search } : {}),
        ...(status ? { status } : {}),
        ...(clientId ? { client_id: clientId } : {}),
      });
      const blob = await apiFetch(`/invoices/export?${query.toString()}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoices_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to export CSV: ' + err.message);
    }
  };

  const handleDownloadPdf = async (invoiceId, invoiceNumber) => {
    try {
      const blob = await apiFetch(`/invoices/${invoiceId}/pdf`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Invoice-${invoiceNumber}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download PDF: ' + err.message);
    }
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    setModalError('');
    setModalLoading(true);

    if (new Date(formData.due_date) < new Date(formData.issue_date)) {
      setModalError('Due date must be on or after issue date');
      setModalLoading(false);
      return;
    }

    try {
      await apiFetch('/invoices', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setShowModal(false);
      setFormData({
        invoice_number: '',
        client_id: clients[0]?.id || '',
        issue_date: new Date().toISOString().split('T')[0],
        due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
        amount: '',
        currency: 'PKR',
        description: '',
        status: 'draft',
      });
      loadInvoices();
    } catch (err) {
      setModalError(err.message || 'Failed to create invoice');
    } finally {
      setModalLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Invoices</h1>
          <p className="page-subtitle">Manage, filter, and track all your client invoices</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button onClick={handleExportCSV} className="btn btn-secondary">
            Export CSV
          </button>
          <button onClick={() => setShowModal(true)} className="btn btn-primary">
            + New Invoice
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card filter-bar">
        <input
          type="text"
          className="form-input filter-search"
          placeholder="Search by invoice number or client name..."
          value={search}
          onChange={(e) => updateParam('search', e.target.value)}
        />

        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={status}
          onChange={(e) => updateParam('status', e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="partially_paid">Partially Paid</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue (Derived)</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={clientId}
          onChange={(e) => updateParam('client_id', e.target.value)}
        >
          <option value="">All Clients</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        <select
          className="form-select"
          style={{ width: 'auto' }}
          value={sort}
          onChange={(e) => updateParam('sort', e.target.value)}
        >
          <option value="due_date">Due Date (Earliest first)</option>
          <option value="-due_date">Due Date (Latest first)</option>
          <option value="amount">Amount (Lowest first)</option>
          <option value="-amount">Amount (Highest first)</option>
        </select>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Invoices Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>Loading invoices...</div>
        ) : invoices.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-title">No invoices found</div>
            <p className="empty-state-text">Try adjusting your filters or create a new invoice.</p>
            <button onClick={() => setShowModal(true)} className="btn btn-primary">
              Create Invoice
            </button>
          </div>
        ) : (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Client</th>
                  <th>Issue Date</th>
                  <th>Due Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Balance Due</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: 600 }}>
                      <Link to={`/invoices/${inv.id}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td>{inv.client?.name || '—'}</td>
                    <td>{inv.issue_date}</td>
                    <td>{inv.due_date}</td>
                    <td style={{ fontWeight: 600 }}>
                      {inv.currency} {inv.amount}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', alignItems: 'center' }}>
                        <span className={`badge badge-${inv.status}`}>{inv.status.replace('_', ' ')}</span>
                        {inv.is_overdue && (
                          <span className="badge badge-overdue">Overdue ({inv.days_late}d)</span>
                        )}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {inv.currency} {inv.balance_due}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                        <Link to={`/invoices/${inv.id}`} className="btn btn-outline btn-sm">
                          View
                        </Link>
                        <button
                          onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)}
                          className="btn btn-outline btn-sm"
                          title="Download PDF"
                        >
                          PDF
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="pagination">
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Showing page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total)
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  disabled={pagination.page <= 1}
                  onClick={() => {
                    const next = new URLSearchParams(searchParams);
                    next.set('page', (pagination.page - 1).toString());
                    setSearchParams(next);
                  }}
                  className="btn btn-outline btn-sm"
                >
                  Previous
                </button>
                <button
                  disabled={pagination.page >= pagination.total_pages}
                  onClick={() => {
                    const next = new URLSearchParams(searchParams);
                    next.set('page', (pagination.page + 1).toString());
                    setSearchParams(next);
                  }}
                  className="btn btn-outline btn-sm"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Create Invoice Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Create New Invoice</h2>
              <button onClick={() => setShowModal(false)} className="modal-close">
                &times;
              </button>
            </div>

            {modalError && <div className="alert alert-error">{modalError}</div>}

            <form onSubmit={handleCreateInvoice}>
              <div className="form-group">
                <label className="form-label">Client *</label>
                {clients.length === 0 ? (
                  <div style={{ fontSize: '0.9rem', color: 'var(--danger)' }}>
                    You have no clients yet. <Link to="/clients">Create a client first</Link>.
                  </div>
                ) : (
                  <select
                    required
                    className="form-select"
                    value={formData.client_id}
                    onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                  >
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Invoice Number *</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. INV-2026-001"
                    value={formData.invoice_number}
                    onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Amount *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    className="form-input"
                    placeholder="25000.00"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Issue Date *</label>
                  <input
                    type="date"
                    required
                    className="form-input"
                    value={formData.issue_date}
                    onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Due Date *</label>
                  <input
                    type="date"
                    required
                    className="form-input"
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Currency</label>
                  <input
                    type="text"
                    maxLength="3"
                    className="form-input"
                    value={formData.currency}
                    onChange={(e) => setFormData({ ...formData, currency: e.target.value.toUpperCase() })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Status</label>
                  <select
                    className="form-select"
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    <option value="draft">Draft</option>
                    <option value="sent">Sent</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Description / Work Scope</label>
                <textarea
                  className="form-textarea"
                  rows="3"
                  placeholder="Notes, deliverables, and payment terms..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={modalLoading || clients.length === 0} className="btn btn-primary">
                  {modalLoading ? 'Saving...' : 'Create Invoice'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
