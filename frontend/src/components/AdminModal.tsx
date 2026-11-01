import React, { useState, useEffect } from 'react';
import {
  X,
  Upload,
  Trash2,
  FileText,
  ShieldAlert,
  Check,
  AlertTriangle,
  Send,
  CheckCircle,
} from 'lucide-react';
import {
  DocumentSummary,
  SupportTicket,
  SalesLead,
  CustomerProfile,
  EscalatedSession,
} from '../types';
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  listTickets,
  resolveTicket,
  listLeads,
  updateLeadStatus,
  listCustomers,
  listEscalations,
  replyToEscalation,
  resolveEscalation,
} from '../services/api';

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = 'tickets' | 'leads' | 'customers' | 'escalations' | 'documents';

export const AdminModal: React.FC<AdminModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<TabType>('tickets');
  const [adminKey, setAdminKey] = useState<string>(
    () => localStorage.getItem('niel_admin_key') || ''
  );

  // Data states
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [leads, setLeads] = useState<SalesLead[]>([]);
  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [escalations, setEscalations] = useState<EscalatedSession[]>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  // Action states
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [agentReplyText, setAgentReplyText] = useState<{ [sid: string]: string }>({});
  const [statusMsg, setStatusMsg] = useState<{ text: string; isError: boolean } | null>(null);

  const handleKeyChange = (val: string) => {
    setAdminKey(val);
    localStorage.setItem('niel_admin_key', val);
  };

  const loadTabData = async () => {
    if (!adminKey.trim()) return;
    setLoading(true);
    setStatusMsg(null);
    try {
      if (activeTab === 'tickets') {
        const data = await listTickets(adminKey);
        setTickets(data);
      } else if (activeTab === 'leads') {
        const data = await listLeads(adminKey);
        setLeads(data);
      } else if (activeTab === 'customers') {
        const data = await listCustomers(adminKey);
        setCustomers(data);
      } else if (activeTab === 'escalations') {
        const data = await listEscalations(adminKey);
        setEscalations(data);
      } else if (activeTab === 'documents') {
        const res = await listDocuments();
        setDocuments(res.documents || []);
      }
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to load tab data', isError: true });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadTabData();
    }
  }, [isOpen, activeTab, adminKey]);

  if (!isOpen) return null;

  // Ticket resolution
  const handleResolveTicket = async (ticketId: string) => {
    try {
      await resolveTicket(ticketId, adminKey);
      setStatusMsg({ text: `Ticket ${ticketId} resolved successfully.`, isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to resolve ticket', isError: true });
    }
  };

  // Lead status update
  const handleUpdateLeadStatus = async (leadId: number, status: string) => {
    try {
      await updateLeadStatus(leadId, status, adminKey);
      setStatusMsg({ text: `Lead #${leadId} updated to ${status}.`, isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to update lead', isError: true });
    }
  };

  // Escalation reply
  const handleSendAgentReply = async (sessionId: string) => {
    const text = agentReplyText[sessionId]?.trim();
    if (!text) return;
    try {
      await replyToEscalation(sessionId, text, adminKey);
      setAgentReplyText((prev) => ({ ...prev, [sessionId]: '' }));
      setStatusMsg({ text: 'Reply sent to visitor.', isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to send reply', isError: true });
    }
  };

  // Escalation resolve
  const handleResolveEscalation = async (sessionId: string) => {
    try {
      await resolveEscalation(sessionId, adminKey);
      setStatusMsg({ text: 'Session returned to AI assistant.', isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Failed to resolve escalation', isError: true });
    }
  };

  // Document upload / delete
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setStatusMsg(null);
      const res = await uploadDocument(file, adminKey);
      setStatusMsg({ text: res.message || 'Document indexed successfully.', isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Upload failed.', isError: true });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document from the vector store?')) return;
    try {
      setStatusMsg(null);
      await deleteDocument(docId, adminKey);
      setStatusMsg({ text: 'Document removed from index.', isError: false });
      loadTabData();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Deletion failed.', isError: true });
    }
  };

  return (
    <div className="niel-modal-backdrop">
      <div className="niel-modal-card niel-modal-expanded">
        <div className="niel-modal-header">
          <div className="niel-modal-title">
            <ShieldAlert size={18} className="niel-admin-icon" />
            <h3>NIEL Agentic Support Operations Dashboard</h3>
          </div>
          <button type="button" className="niel-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Dashboard Navigation Tabs */}
        <div className="niel-admin-tabs-bar">
          <button
            type="button"
            className={`niel-tab-btn ${activeTab === 'tickets' ? 'active' : ''}`}
            onClick={() => setActiveTab('tickets')}
          >
            Support Tickets {tickets.length > 0 && `(${tickets.length})`}
          </button>
          <button
            type="button"
            className={`niel-tab-btn ${activeTab === 'leads' ? 'active' : ''}`}
            onClick={() => setActiveTab('leads')}
          >
            Sales Leads {leads.length > 0 && `(${leads.length})`}
          </button>
          <button
            type="button"
            className={`niel-tab-btn ${activeTab === 'customers' ? 'active' : ''}`}
            onClick={() => setActiveTab('customers')}
          >
            Customer Profiles {customers.length > 0 && `(${customers.length})`}
          </button>
          <button
            type="button"
            className={`niel-tab-btn ${activeTab === 'escalations' ? 'active' : ''}`}
            onClick={() => setActiveTab('escalations')}
          >
            Live Escalations {escalations.length > 0 && `(${escalations.length})`}
          </button>
          <button
            type="button"
            className={`niel-tab-btn ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            Knowledge Base Docs
          </button>
        </div>

        <div className="niel-modal-body">
          {/* Admin Auth Input */}
          <div className="niel-admin-auth-box">
            <label htmlFor="adminKey">Admin Key (X-Admin-Key):</label>
            <input
              id="adminKey"
              type="password"
              placeholder="Enter ADMIN_API_KEY..."
              value={adminKey}
              onChange={(e) => handleKeyChange(e.target.value)}
              className="niel-admin-input"
            />
          </div>

          {statusMsg && (
            <div className={`niel-status-banner ${statusMsg.isError ? 'niel-banner-error' : 'niel-banner-success'}`}>
              {statusMsg.isError ? <AlertTriangle size={14} /> : <Check size={14} />}
              <span>{statusMsg.text}</span>
            </div>
          )}

          {/* TAB 1: SUPPORT TICKETS */}
          {activeTab === 'tickets' && (
            <div className="niel-tab-content">
              <h4>Active & Resolved Support Tickets</h4>
              {loading ? (
                <p className="niel-loading-text">Loading support tickets...</p>
              ) : tickets.length === 0 ? (
                <p className="niel-empty-text">No support tickets recorded yet.</p>
              ) : (
                <table className="niel-docs-table">
                  <thead>
                    <tr>
                      <th>Ticket ID</th>
                      <th>Category</th>
                      <th>Issue Description</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tickets.map((t) => (
                      <tr key={t.id}>
                        <td className="niel-text-bold">{t.id}</td>
                        <td>{t.product_category}</td>
                        <td className="niel-desc-cell">{t.issue_description}</td>
                        <td>
                          <span className={`niel-badge niel-severity-${t.severity.toLowerCase()}`}>
                            {t.severity}
                          </span>
                        </td>
                        <td>
                          <span className={`niel-badge niel-status-${t.status.toLowerCase()}`}>
                            {t.status}
                          </span>
                        </td>
                        <td>
                          {t.status !== 'RESOLVED' && (
                            <button
                              type="button"
                              className="niel-btn-action"
                              onClick={() => handleResolveTicket(t.id)}
                            >
                              Resolve
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* TAB 2: SALES LEADS */}
          {activeTab === 'leads' && (
            <div className="niel-tab-content">
              <h4>Qualified Commercial Sales Leads</h4>
              {loading ? (
                <p className="niel-loading-text">Loading sales leads...</p>
              ) : leads.length === 0 ? (
                <p className="niel-empty-text">No commercial leads logged yet.</p>
              ) : (
                <table className="niel-docs-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Product Interest</th>
                      <th>Qty</th>
                      <th>Location / Details</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Update Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((l) => (
                      <tr key={l.id}>
                        <td>#{l.id}</td>
                        <td className="niel-text-bold">{l.product_interest}</td>
                        <td>{l.required_quantity || '—'}</td>
                        <td className="niel-desc-cell">{l.requirement_details || l.location || '—'}</td>
                        <td>
                          <span className={`niel-badge niel-priority-${l.priority.toLowerCase()}`}>
                            {l.priority}
                          </span>
                        </td>
                        <td>
                          <span className={`niel-badge niel-status-${l.status.toLowerCase()}`}>
                            {l.status}
                          </span>
                        </td>
                        <td>
                          <select
                            className="niel-status-select"
                            value={l.status}
                            onChange={(e) => handleUpdateLeadStatus(l.id, e.target.value)}
                          >
                            <option value="NEW">NEW</option>
                            <option value="QUALIFIED">QUALIFIED</option>
                            <option value="CONTACTED">CONTACTED</option>
                            <option value="CLOSED">CLOSED</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* TAB 3: CUSTOMER PROFILES */}
          {activeTab === 'customers' && (
            <div className="niel-tab-content">
              <h4>Registered Customer Directory & Consented Preferences</h4>
              {loading ? (
                <p className="niel-loading-text">Loading customer profiles...</p>
              ) : customers.length === 0 ? (
                <p className="niel-empty-text">No customer profiles registered yet.</p>
              ) : (
                <div className="niel-customer-cards-grid">
                  {customers.map((c) => (
                    <div key={c.customer_id} className="niel-customer-card">
                      <div className="niel-cust-header">
                        <h5>{c.name || 'Anonymous Customer'}</h5>
                        <span className="niel-badge niel-consent-badge">
                          {c.has_consented ? 'Consented' : 'Unconfirmed'}
                        </span>
                      </div>
                      <p className="niel-cust-company">{c.company || 'Company not specified'}</p>
                      {c.email && <p className="niel-cust-detail"><strong>Email:</strong> {c.email}</p>}
                      {c.phone && <p className="niel-cust-detail"><strong>Phone:</strong> {c.phone}</p>}
                      {c.industry && <p className="niel-cust-detail"><strong>Industry:</strong> {c.industry}</p>}
                      {c.interests && c.interests.length > 0 && (
                        <div className="niel-tags-row">
                          {c.interests.map((tag: string, i: number) => (
                            <span key={i} className="niel-tag">{tag}</span>
                          ))}
                        </div>
                      )}
                      <div className="niel-cust-stats">
                        <span>Open Tickets: <strong>{c.open_tickets_count}</strong></span>
                        <span>Recent Leads: <strong>{c.recent_leads?.length || 0}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: LIVE ESCALATIONS */}
          {activeTab === 'escalations' && (
            <div className="niel-tab-content">
              <h4>Human Escalation Queue</h4>
              {loading ? (
                <p className="niel-loading-text">Checking escalated sessions...</p>
              ) : escalations.length === 0 ? (
                <p className="niel-empty-text">No sessions currently waiting for human intervention.</p>
              ) : (
                <div className="niel-escalations-list">
                  {escalations.map((esc) => (
                    <div key={esc.session_id} className="niel-escalation-item">
                      <div className="niel-esc-header">
                        <span className="niel-text-bold">Session: {esc.session_id}</span>
                        <span className="niel-badge niel-badge-escalated">Escalated</span>
                      </div>
                      <p className="niel-esc-lastmsg">
                        <strong>Last Message ({esc.last_message_role || 'user'}):</strong> {esc.last_message || '—'}
                      </p>
                      <div className="niel-esc-actions">
                        <input
                          type="text"
                          placeholder="Type response to visitor..."
                          className="niel-esc-input"
                          value={agentReplyText[esc.session_id] || ''}
                          onChange={(e) =>
                            setAgentReplyText((prev) => ({ ...prev, [esc.session_id]: e.target.value }))
                          }
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSendAgentReply(esc.session_id);
                          }}
                        />
                        <button
                          type="button"
                          className="niel-btn-action"
                          onClick={() => handleSendAgentReply(esc.session_id)}
                        >
                          <Send size={12} /> Send Reply
                        </button>
                        <button
                          type="button"
                          className="niel-btn-resolve"
                          onClick={() => handleResolveEscalation(esc.session_id)}
                        >
                          <CheckCircle size={12} /> Return to AI
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: DOCUMENTS INVENTORY */}
          {activeTab === 'documents' && (
            <div className="niel-tab-content">
              <div className="niel-upload-section">
                <label className="niel-upload-btn">
                  <Upload size={14} />
                  <span>{uploading ? 'Extracting & Indexing...' : 'Upload Technical Brochure (PDF)'}</span>
                  <input
                    type="file"
                    accept=".pdf,.txt,.md"
                    onChange={handleUpload}
                    disabled={uploading}
                    style={{ display: 'none' }}
                  />
                </label>
                <span className="niel-upload-hint">Upload official manuals, datasheets, or certificates.</span>
              </div>

              <div className="niel-docs-table-wrapper">
                <h4>Indexed Technical Catalogues ({documents.length})</h4>
                {loading ? (
                  <p className="niel-loading-text">Loading catalog inventory...</p>
                ) : documents.length === 0 ? (
                  <p className="niel-empty-text">No documents indexed in local vector store.</p>
                ) : (
                  <table className="niel-docs-table">
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Pages</th>
                        <th>Chunks</th>
                        <th>Date</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.doc_id}>
                          <td className="niel-doc-filename" title={doc.doc_id}>
                            <FileText size={14} />
                            <span>{doc.filename}</span>
                          </td>
                          <td>{doc.page_count}</td>
                          <td>{doc.chunk_count}</td>
                          <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                          <td>
                            <button
                              type="button"
                              className="niel-del-btn"
                              onClick={() => handleDeleteDoc(doc.doc_id)}
                              title="Delete document and remove all vector embeddings"
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
