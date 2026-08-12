import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';
import { POLL_INTERVAL_MS } from '../lib/constants';
import type { Discussion, DiscussionListResponse } from '../types';
import DiscussionCard from '../components/DiscussionCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

export default function HomePage() {
  const navigate = useNavigate();
  const { data, error, loading, refetch } = useApi<DiscussionListResponse>(
    () => api.listDiscussions(),
  );

  // Poll if any discussion is active
  useEffect(() => {
    if (!data) return;
    const hasActive = data.discussions.some((d) => d.status === 'active');
    if (!hasActive) return;

    const interval = setInterval(refetch, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [data, refetch]);

  const handleCardClick = (discussion: Discussion) => {
    if (discussion.status === 'pending') {
      navigate(`/generate?discussion_id=${discussion.id}`);
    } else {
      navigate(`/studio/${discussion.id}`);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <header className="mb-10 flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🎙️</span>
          <h1 className="text-2xl font-bold text-white">
            AI Panel Studio
          </h1>
        </div>
        <button
          onClick={() => navigate('/generate')}
          data-testid="new-discussion-btn"
          className="rounded-xl bg-gradient-to-r from-studio-accent to-blue-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-studio-accent/25 transition-all hover:shadow-xl hover:shadow-studio-accent/40 hover:-translate-y-0.5 active:translate-y-0"
        >
          + 发起新讨论
        </button>
      </header>

      {/* Content */}
      {loading && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          <LoadingSkeleton variant="card" count={4} />
        </div>
      )}

      {error && !loading && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-500/20 bg-red-500/5 py-16">
          <span className="text-4xl">⚠️</span>
          <p className="text-gray-400">{error}</p>
          <button
            onClick={refetch}
            className="rounded-lg border border-studio-border px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-studio-border/30"
          >
            重试
          </button>
        </div>
      )}

      {data && data.discussions.length === 0 && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-studio-border bg-studio-card py-20">
          <span className="text-6xl">🎙️</span>
          <h2 className="text-xl font-semibold text-white">
            还没有讨论
          </h2>
          <p className="text-gray-400">
            来发起第一场 AI 圆桌吧！
          </p>
          <button
            onClick={() => navigate('/generate')}
            className="mt-4 rounded-xl bg-gradient-to-r from-studio-accent to-blue-500 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-studio-accent/25 transition-all hover:-translate-y-0.5"
          >
            发起新讨论
          </button>
        </div>
      )}

      {data && data.discussions.length > 0 && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {data.discussions.map((discussion) => (
            <DiscussionCard
              key={discussion.id}
              discussion={discussion}
              onClick={() => handleCardClick(discussion)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
