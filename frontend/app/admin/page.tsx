'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { adminApi, documentApi } from '@/lib/api';
import { Document, AnalyticsData } from '@/types';
import {
  BarChart2, FileText, MessageSquare, ThumbsUp, ThumbsDown,
  Upload, Trash2, RefreshCw, ChevronLeft, CheckCircle2,
  AlertCircle, Clock, Loader2
} from 'lucide-react';

export default function AdminPage() {
  const { user, isAdmin } = useAuth();
  const router = useRouter();

  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({ title: '', department: '', category: '' });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState<'analytics' | 'documents'>('analytics');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAdmin) { router.push('/chat'); return; }
    loadData();
  }, [isAdmin]);

  const loadData = async () => {
    const [analyticsData, docsData] = await Promise.all([
      adminApi.analytics().catch(() => null),
      documentApi.list().catch(() => ({ documents: [] })),
    ]);
    if (analyticsData) setAnalytics(analyticsData);
    setDocuments(docsData.documents || []);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('title', uploadForm.title || uploadFile.name);
    if (uploadForm.department) formData.append('department', uploadForm.department);
    if (uploadForm.category) formData.append('document_category', uploadForm.category);

    try {
      await documentApi.upload(formData);
      setUploadForm({ title: '', department: '', category: '' });
      setUploadFile(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document? This cannot be undone.')) return;
    await documentApi.delete(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  const handleReindex = async (id: string) => {
    await documentApi.reindex(id);
    await loadData();
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={14} className="text-green-400" />;
      case 'processing': return <Loader2 size={14} className="text-yellow-400 animate-spin" />;
      case 'failed': return <AlertCircle size={14} className="text-red-400" />;
      default: return <Clock size={14} className="text-zinc-500" />;
    }
  };

  if (!isAdmin) return null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="glass border-b border-zinc-800/50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push('/chat')} className="btn-ghost py-1.5 px-2">
            <ChevronLeft size={16} />
            Back
          </button>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">W</span>
            </div>
            <h1 className="font-bold text-lg gradient-text">Admin Dashboard</h1>
          </div>
        </div>
        <p className="text-xs text-zinc-500">Logged in as {user?.email}</p>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tab Navigation */}
        <div className="flex gap-2 mb-8 bg-zinc-900 p-1 rounded-xl w-fit">
          {(['analytics', 'documents'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab
                  ? 'bg-violet-600 text-white shadow'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab === 'analytics' ? <BarChart2 size={14} className="inline mr-1.5" /> : <FileText size={14} className="inline mr-1.5" />}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* ── Analytics Tab ──────────────────────────────────────────── */}
        {activeTab === 'analytics' && analytics && (
          <div className="flex flex-col gap-6">
            {/* Stats grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Conversations', value: analytics.total_conversations, icon: <MessageSquare size={20} className="text-violet-400" /> },
                { label: 'Messages', value: analytics.total_messages, icon: <MessageSquare size={20} className="text-indigo-400" /> },
                { label: 'Documents', value: analytics.total_documents, icon: <FileText size={20} className="text-blue-400" /> },
                { label: 'Helpful %', value: `${analytics.helpful_percentage}%`, icon: <ThumbsUp size={20} className="text-green-400" /> },
              ].map((stat) => (
                <div key={stat.label} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-zinc-400 text-sm">{stat.label}</span>
                    {stat.icon}
                  </div>
                  <p className="text-3xl font-bold gradient-text">{stat.value}</p>
                </div>
              ))}
            </div>

            {/* Feedback breakdown */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-zinc-300 mb-4">Feedback Summary</h3>
                <div className="flex gap-4">
                  <div className="flex items-center gap-2">
                    <ThumbsUp size={16} className="text-green-400" />
                    <span className="text-2xl font-bold text-green-400">{analytics.helpful_count}</span>
                    <span className="text-zinc-500 text-sm">Helpful</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <ThumbsDown size={16} className="text-red-400" />
                    <span className="text-2xl font-bold text-red-400">{analytics.not_helpful_count}</span>
                    <span className="text-zinc-500 text-sm">Not helpful</span>
                  </div>
                </div>
                {analytics.helpful_count + analytics.not_helpful_count > 0 && (
                  <div className="mt-4 bg-zinc-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all"
                      style={{ width: `${analytics.helpful_percentage}%` }}
                    />
                  </div>
                )}
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-zinc-300 mb-4">Documents by Status</h3>
                <div className="flex flex-col gap-2">
                  {Object.entries(analytics.documents_by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {statusIcon(status)}
                        <span className="text-sm text-zinc-400 capitalize">{status}</span>
                      </div>
                      <span className="text-sm font-bold text-zinc-200">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Tool usage */}
            {Object.keys(analytics.tool_usage_count).length > 0 && (
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5">
                <h3 className="text-sm font-semibold text-zinc-300 mb-4">MCP Tool Usage</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(analytics.tool_usage_count).map(([tool, count]) => (
                    <div key={tool} className="bg-zinc-800 rounded-lg px-3 py-2 text-xs">
                      <span className="text-violet-400 font-mono">{tool}</span>
                      <span className="text-zinc-400 ml-2">{count}×</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Documents Tab ──────────────────────────────────────────── */}
        {activeTab === 'documents' && (
          <div className="flex flex-col gap-6">
            {/* Upload form */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
              <h3 className="text-sm font-semibold text-zinc-300 mb-4">Upload Document</h3>
              <form onSubmit={handleUpload} className="flex flex-col gap-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="md:col-span-1">
                    <label className="label">Title</label>
                    <input
                      type="text"
                      className="input"
                      placeholder="Academic Calendar 2026"
                      value={uploadForm.title}
                      onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="label">Department (optional)</label>
                    <input
                      type="text"
                      className="input"
                      placeholder="Computer Engineering"
                      value={uploadForm.department}
                      onChange={(e) => setUploadForm({ ...uploadForm, department: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="label">Category (optional)</label>
                    <input
                      type="text"
                      className="input"
                      placeholder="academic, policy, notice…"
                      value={uploadForm.category}
                      onChange={(e) => setUploadForm({ ...uploadForm, category: e.target.value })}
                    />
                  </div>
                </div>

                <div
                  className="border-2 border-dashed border-zinc-700 rounded-xl p-8 text-center cursor-pointer hover:border-violet-500/50 transition-colors"
                  onClick={() => document.getElementById('file-input')?.click()}
                >
                  <input
                    id="file-input"
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.txt,.csv,.pptx,.xlsx"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                  <Upload size={24} className="mx-auto mb-2 text-zinc-500" />
                  {uploadFile ? (
                    <p className="text-sm text-violet-400 font-medium">{uploadFile.name}</p>
                  ) : (
                    <>
                      <p className="text-sm text-zinc-400">Click to upload or drag & drop</p>
                      <p className="text-xs text-zinc-600 mt-1">PDF, DOCX, TXT, CSV, PPTX, XLSX (max 50MB)</p>
                    </>
                  )}
                </div>

                {error && (
                  <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl px-4 py-3">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  className="btn-primary self-start"
                  disabled={!uploadFile || uploading}
                >
                  {uploading ? (
                    <><Loader2 size={14} className="animate-spin" /> Processing…</>
                  ) : (
                    <><Upload size={14} /> Upload & Index</>
                  )}
                </button>
              </form>
            </div>

            {/* Documents table */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-zinc-300">Knowledge Base ({documents.length})</h3>
                <button onClick={loadData} className="btn-ghost py-1 text-xs">
                  <RefreshCw size={12} /> Refresh
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-zinc-500 text-xs uppercase tracking-wide border-b border-zinc-800">
                      <th className="px-6 py-3 text-left">Title</th>
                      <th className="px-6 py-3 text-left">Type</th>
                      <th className="px-6 py-3 text-left">Department</th>
                      <th className="px-6 py-3 text-left">Status</th>
                      <th className="px-6 py-3 text-left">Chunks</th>
                      <th className="px-6 py-3 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-12 text-center text-zinc-600 text-sm">
                          No documents uploaded yet. Upload your first document above.
                        </td>
                      </tr>
                    ) : (
                      documents.map((doc) => (
                        <tr key={doc.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                          <td className="px-6 py-4">
                            <p className="text-zinc-200 font-medium">{doc.title}</p>
                            <p className="text-zinc-600 text-xs mt-0.5">{doc.file_name}</p>
                          </td>
                          <td className="px-6 py-4">
                            <span className="bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded text-xs uppercase">
                              {doc.document_type}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-zinc-400 text-xs">
                            {doc.department || '—'}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-1.5">
                              {statusIcon(doc.indexing_status)}
                              <span className="text-xs text-zinc-400 capitalize">
                                {doc.indexing_status}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-zinc-400 text-xs">{doc.chunk_count}</td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleReindex(doc.id)}
                                className="btn-ghost py-1 px-2 text-xs"
                                title="Re-index"
                              >
                                <RefreshCw size={12} />
                              </button>
                              <button
                                onClick={() => handleDelete(doc.id)}
                                className="btn-ghost py-1 px-2 text-xs text-red-400 hover:text-red-300"
                                title="Delete"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
