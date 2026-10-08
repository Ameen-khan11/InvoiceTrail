import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

export default function Clients() {
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Modal create/edit state
  const [showModal, setShowModal] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    phone: '',
    notes: '',
  });

  // Client detail view modal (invoices and billed vs received)
  const [selectedClientDetail, setSelectedClientDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadClients = async (query = '') => {
    setLoading(true);
    setError('');
    try {
      const res = await apiFetch(`/clients?search=${encodeURIComponent(query)}`);
      setClients(res.clients || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch clients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClients(search);
  }, [search]);

  const openCreateModal = () => {
    setEditingClient(null);
    setFormData({ name: '', email: '', company: '', phone: '', notes: '' });
    setModalError('');
    setShowModal(true);
  };

  const openEditModal = (client) => {
    setEditingClient(client);
    setFormData({
      name: client.name,
      email: client.email,
      company: client.company || '',
      phone: client.phone || '',
      notes: client.notes || '',
    });
    setModalError('');
    setShowModal(true);
  };

  const handleSaveClient = async (e) => {
    e.preventDefault();
    setModalError('');
    setModalLoading(true);

    try {
      if (editingClient) {
        await apiFetch(`/clients/${editingClient.id}`, {
          method: 'PUT',
          body: JSON.stringify(formData),
        });
        setSuccess('Client updated successfully');
      } else {
        await apiFetch('/clients', {
          method: 'POST',
          body: JSON.stringify(formData),
        });
        setSuccess('Client created successfully');
      }
      setShowModal(false);
      loadClients(search);
    } catch (err) {
      setModalError(err.message || 'Failed to save client');
    } finally {
      setModalLoading(false);
    }
  };

  const handleDeleteClient = async (client) => {
    if (!window.confirm(`Are you sure you want to delete client "${client.name}"?`)) {
      return;
    }
    setError('');
    setSuccess('');

    try {
      await apiFetch(`/clients/${client.id}`, {
        method: 'DELETE',
      });
      setSuccess(`Client "${client.name}" deleted successfully`);
      loadClients(search);
    } catch (err) {
      setError(err.message || 'Failed to delete client');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const viewClientDetail = async (client) => {
    setDetailLoading(true);
    setSelectedClientDetail(null);
    try {
      const res = await apiFetch(`/clients/${client.id}`);
      setSelectedClientDetail(res);
    } catch (err) {
      setError('Failed to load client details: ' + err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Clients</h1>
          <p className="page-subtitle">Manage your clients and view their total billed vs received</p>
        </div>
        <div>
          <button onClick={openCreateModal} className="btn btn-primary">
            + New Client
          </button>
        </div>
      </div>

      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Search Bar */}
      <div className="card filter-bar">
        <input
          type="text"
          className="form-input filter-search"
          placeholder="Search by name, company, or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Clients Table */}
      <div className="table-container">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>Loading clients...</div>
        ) : clients.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-title">No clients found</div>
            <p className="empty-state-text">Add your first client to start creating invoices.</p>
            <button onClick={openCreateModal} className="btn btn-primary">
              Create Client
            </button>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Company</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.id}>
                  <td style={{ fontWeight: 600 }}>{c.name}</td>
                  <td>{c.company || '—'}</td>
                  <td>{c.email}</td>
                  <td>{c.phone || '—'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      <button onClick={() => viewClientDetail(c)} className="btn btn-outline btn-sm">
                        Details & Invoices
                      </button>
                      <button onClick={() => openEditModal(c)} className="btn btn-outline btn-sm">
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteClient(c)}
                        className="btn btn-outline btn-sm"
                        style={{ color: 'var(--danger)' }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create / Edit Client Modal */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">{editingClient ? 'Edit Client' : 'Create New Client'}</h2>
              <button onClick={() => setShowModal(false)} className="modal-close">
                &times;
              </button>
            </div>

            {modalError && <div className="alert alert-error">{modalError}</div>}

            <form onSubmit={handleSaveClient}>
              <div className="form-group">
                <label className="form-label">Client Name *</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. Acme Corporation"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input
                  type="email"
                  required
                  className="form-input"
                  placeholder="billing@acme.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label">Company</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Acme Global Inc."
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="+92 300 1234567"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Notes</label>
                <textarea
                  className="form-textarea"
                  rows="2"
                  placeholder="Payment terms, contact person, etc."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setShowModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={modalLoading} className="btn btn-primary">
                  {modalLoading ? 'Saving...' : editingClient ? 'Update Client' : 'Create Client'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Client Detail View Modal (AC-3.3) */}
      {selectedClientDetail && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: 640 }}>
            <div className="modal-header">
              <div>
                <h2 className="modal-title">{selectedClientDetail.name}</h2>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  {selectedClientDetail.company && `${selectedClientDetail.company} • `}
                  {selectedClientDetail.email}
                </div>
              </div>
              <button onClick={() => setSelectedClientDetail(null)} className="modal-close">
                &times;
              </button>
            </div>

            {/* Total Billed vs Total Received Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: 8, border: '1px solid var(--border)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Total Billed
                </div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>Rs. {selectedClientDetail.total_billed}</div>
              </div>

              <div style={{ background: '#ecfdf5', padding: '1rem', borderRadius: 8, border: '1px solid #a7f3d0' }}>
                <div style={{ fontSize: '0.8rem', color: '#047857', textTransform: 'uppercase' }}>
                  Total Received
                </div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#047857' }}>
                  Rs. {selectedClientDetail.total_received}
                </div>
              </div>
            </div>

            {/* Invoices List */}
            <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              Client Invoices ({selectedClientDetail.invoices?.length || 0})
            </h3>

            {selectedClientDetail.invoices?.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1rem', textAlign: 'center' }}>
                No invoices found for this client.
              </div>
            ) : (
              <div className="table-container" style={{ maxHeight: 240, overflowY: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Number</th>
                      <th>Due Date</th>
                      <th>Amount</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedClientDetail.invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td>
                          <Link to={`/invoices/${inv.id}`} style={{ color: 'var(--primary)', fontWeight: 600 }}>
                            {inv.invoice_number}
                          </Link>
                        </td>
                        <td>{inv.due_date}</td>
                        <td style={{ fontWeight: 600 }}>
                          {inv.currency} {inv.amount}
                        </td>
                        <td>
                          {inv.is_overdue ? (
                            <span className="badge badge-overdue">Overdue</span>
                          ) : (
                            <span className={`badge badge-${inv.status}`}>{inv.status.replace('_', ' ')}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="modal-actions">
              <button onClick={() => setSelectedClientDetail(null)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
