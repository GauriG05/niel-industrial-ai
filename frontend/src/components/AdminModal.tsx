import React, { useState, useEffect } from 'react';
import { X, Upload, Trash2, FileText, ShieldAlert, Check } from 'lucide-react';
import { DocumentSummary } from '../types';
import { listDocuments, uploadDocument, deleteDocument } from '../services/api';

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AdminModal: React.FC<AdminModalProps> = ({ isOpen, onClose }) => {
  const [adminKey, setAdminKey] = useState('');
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; isError: boolean } | null>(null);

  const fetchDocs = async () => {
    try {
      setLoading(true);
      const res = await listDocuments();
      setDocuments(res.documents);
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Error loading documents', isError: true });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDocs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!adminKey.trim()) {
      setStatusMsg({ text: 'Please enter the Admin Secret Key before uploading.', isError: true });
      return;
    }
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      setStatusMsg(null);
      const res = await uploadDocument(file, adminKey);
      setStatusMsg({ text: res.message || 'Document indexed successfully.', isError: false });
      await fetchDocs();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Upload failed.', isError: true });
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDelete = async (docId: string) => {
    if (!adminKey.trim()) {
      setStatusMsg({ text: 'Please enter Admin Secret Key to delete documents.', isError: true });
      return;
    }
    if (!confirm('Are you sure you want to remove this document and all its indexed chunks?')) return;

    try {
      setStatusMsg(null);
      await deleteDocument(docId, adminKey);
      setStatusMsg({ text: 'Document removed from index.', isError: false });
      await fetchDocs();
    } catch (err: any) {
      setStatusMsg({ text: err.message || 'Deletion failed.', isError: true });
    }
  };

  return (
    <div className="niel-modal-backdrop">
      <div className="niel-modal-card">
        <div className="niel-modal-header">
          <div className="niel-modal-title">
            <ShieldAlert size={18} className="niel-admin-icon" />
            <h3>Authorized Document Management</h3>
          </div>
          <button type="button" className="niel-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="niel-modal-body">
          <div className="niel-admin-auth-box">
            <label htmlFor="adminKey">Admin Key (Backend Authorization):</label>
            <input
              id="adminKey"
              type="password"
              placeholder="Enter ADMIN_API_KEY..."
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              className="niel-admin-input"
            />
          </div>

          {statusMsg && (
            <div className={`niel-status-banner ${statusMsg.isError ? 'niel-banner-error' : 'niel-banner-success'}`}>
              {statusMsg.isError ? <ShieldAlert size={14} /> : <Check size={14} />}
              <span>{statusMsg.text}</span>
            </div>
          )}

          <div className="niel-upload-section">
            <label className="niel-upload-btn">
              <Upload size={14} />
              <span>{uploading ? 'Extracting & Indexing...' : 'Upload Authorized PDF'}</span>
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={handleUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>
            <span className="niel-upload-hint">Supported: PDF, TXT. Content inspected for text density.</span>
          </div>

          <div className="niel-docs-table-wrapper">
            <h4>Indexed Document Inventory ({documents.length})</h4>
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
                          onClick={() => handleDelete(doc.doc_id)}
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
      </div>
    </div>
  );
};

