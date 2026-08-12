import { useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { useApi } from '../hooks/useApi';
import {
  DEFAULT_EXPERT_COUNT,
  DEFAULT_MAX_ROUNDS,
} from '../lib/constants';
import type {
  DiscussionDetail,
  GenerateGuestsResponse,
  Guest,
} from '../types';
import TopicInput from '../components/TopicInput';
import GuestCountSlider from '../components/GuestCountSlider';
import GuestCard from '../components/GuestCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

export default function GuestGenerationPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const discussionId = searchParams.get('discussion_id');

  // --- Config mode state ---
  const [topic, setTopic] = useState('');
  const [expertCount, setExpertCount] = useState(DEFAULT_EXPERT_COUNT);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // --- Generate mode state ---
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [guests, setGuests] = useState<Guest[] | null>(null);

  // --- Confirm mode state ---
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  // Load discussion detail if we have an ID
  const { data: discussion, loading: detailLoading } = useApi<DiscussionDetail>(
    () => api.getDiscussion(discussionId!),
    [discussionId],
  );

  // Derive mode from state
  const hasGuests = !!(
    (discussion?.guests && discussion.guests.length > 0) ||
    guests
  );
  const displayGuests = guests || discussion?.guests || [];

  // --- Mode 1: Create Discussion ---
  const handleCreate = useCallback(async () => {
    if (!topic.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      const result = await api.createDiscussion({
        topic: topic.trim(),
        expert_count: expertCount,
        max_rounds: DEFAULT_MAX_ROUNDS,
      });
      navigate(`/generate?discussion_id=${result.id}`, { replace: true });
    } catch (err) {
      setCreateError(
        err instanceof ApiError ? err.message : '创建讨论失败，请重试',
      );
    } finally {
      setCreating(false);
    }
  }, [topic, expertCount, navigate]);

  // --- Mode 2: Generate Guests ---
  const handleGenerate = useCallback(async () => {
    if (!discussionId) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      const result: GenerateGuestsResponse =
        await api.generateGuests(discussionId);
      setGuests(result.guests);
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        setGenerateError('AI 服务暂不可用，请稍后重试');
      } else {
        setGenerateError(
          err instanceof ApiError ? err.message : '生成嘉宾失败，请重试',
        );
      }
    } finally {
      setGenerating(false);
    }
  }, [discussionId]);

  // --- Mode 3: Confirm and Start Discussion ---
  const handleConfirm = useCallback(async () => {
    if (!discussionId) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      await api.confirmDiscussion(discussionId);
      navigate(`/studio/${discussionId}`);
    } catch (err) {
      setConfirmError(
        err instanceof ApiError ? err.message : '确认讨论失败，请重试',
      );
    } finally {
      setConfirming(false);
    }
  }, [discussionId, navigate]);

  const handleRegenerate = useCallback(() => {
    setGuests(null);
    setGenerateError(null);
  }, []);

  // --- Render ---

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Back link */}
      <button
        onClick={() => navigate('/')}
        className="mb-6 inline-flex items-center gap-1 text-sm text-gray-400 transition-colors hover:text-white"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        返回首页
      </button>

      <div className="flex flex-col gap-8 lg:flex-row">
        {/* Left: Config area (40%) */}
        <div className="flex-shrink-0 lg:w-[40%]">
          <div className="sticky top-8 rounded-xl border border-studio-border bg-studio-card p-6">
            <h2 className="mb-6 text-xl font-bold text-white">
              {discussionId
                ? hasGuests
                  ? '确认嘉宾阵容'
                  : '生成嘉宾阵容'
                : '发起新讨论'}
            </h2>

            {/* Mode 1: Config */}
            {!discussionId && (
              <div className="space-y-6">
                <TopicInput
                  value={topic}
                  onChange={setTopic}
                  disabled={creating}
                />
                <GuestCountSlider
                  value={expertCount}
                  onChange={setExpertCount}
                  disabled={creating}
                />
                {createError && (
                  <p className="text-sm text-red-400">{createError}</p>
                )}
                <button
                  onClick={handleCreate}
                  disabled={!topic.trim() || creating}
                  className="w-full rounded-xl bg-gradient-to-r from-studio-accent to-blue-500 py-3 text-sm font-semibold text-white shadow-lg shadow-studio-accent/25 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                >
                  {creating ? (
                    <span className="inline-flex items-center gap-2">
                      <svg
                        className="h-4 w-4 animate-spin"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      创建中...
                    </span>
                  ) : (
                    '创建讨论'
                  )}
                </button>
              </div>
            )}

            {/* Mode 2: Generate */}
            {discussionId && !hasGuests && (
              <div className="space-y-6">
                {detailLoading ? (
                  <LoadingSkeleton variant="text" />
                ) : (
                  <>
                    <div className="rounded-xl border border-studio-border bg-studio-bg/50 p-4">
                      <p className="text-xs text-gray-500 mb-1">讨论话题</p>
                      <p className="text-white font-medium">
                        {discussion?.topic || '加载中...'}
                      </p>
                    </div>
                    {generateError && (
                      <p className="text-sm text-red-400">{generateError}</p>
                    )}
                    <button
                      onClick={handleGenerate}
                      disabled={generating}
                      data-testid="generate-btn"
                      className="w-full rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-500/25 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                    >
                      {generating ? (
                        <span className="inline-flex items-center gap-2">
                          <svg
                            className="h-4 w-4 animate-spin"
                            viewBox="0 0 24 24"
                            fill="none"
                          >
                            <circle
                              className="opacity-25"
                              cx="12"
                              cy="12"
                              r="10"
                              stroke="currentColor"
                              strokeWidth="4"
                            />
                            <path
                              className="opacity-75"
                              fill="currentColor"
                              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                            />
                          </svg>
                          正在生成嘉宾阵容...
                        </span>
                      ) : (
                        '✨ 生成阵容'
                      )}
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Mode 3: Confirm */}
            {discussionId && hasGuests && (
              <div className="space-y-6">
                <div className="rounded-xl border border-studio-border bg-studio-bg/50 p-4">
                  <p className="text-xs text-gray-500 mb-1">讨论话题</p>
                  <p className="text-white font-medium">
                    {discussion?.topic}
                  </p>
                </div>

                <div className="flex items-center gap-3 text-sm text-gray-400">
                  <span>👥 {displayGuests.length} 位嘉宾</span>
                  <span>·</span>
                  <span>🔄 {discussion?.max_rounds || DEFAULT_MAX_ROUNDS} 轮讨论</span>
                </div>

                <button
                  onClick={handleRegenerate}
                  className="text-sm text-gray-500 underline transition-colors hover:text-gray-300"
                >
                  重新生成阵容
                </button>

                {confirmError && (
                  <p className="text-sm text-red-400">{confirmError}</p>
                )}

                <button
                  onClick={handleConfirm}
                  disabled={confirming}
                  data-testid="confirm-btn"
                  className="w-full rounded-xl bg-gradient-to-r from-studio-accent to-blue-500 py-3 text-sm font-semibold text-white shadow-lg shadow-studio-accent/25 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                >
                  {confirming ? (
                    <span className="inline-flex items-center gap-2">
                      <svg
                        className="h-4 w-4 animate-spin"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                      </svg>
                      确认中...
                    </span>
                  ) : (
                    '🎬 确认阵容，进入演播厅'
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right: Guest Preview (60%) */}
        <div className="flex-1 lg:w-[60%]">
          {!discussionId && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-studio-border bg-studio-card py-20">
              <span className="text-6xl mb-4">🎭</span>
              <p className="text-gray-400">
                输入话题并创建讨论后，这里将展示 AI 生成的嘉宾阵容
              </p>
            </div>
          )}

          {discussionId && !hasGuests && !detailLoading && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-studio-border bg-studio-card py-20">
              <span className="text-6xl mb-4">🤖</span>
              <p className="text-gray-400">
                点击「生成阵容」按钮，AI 将为你的话题匹配最合适的嘉宾
              </p>
            </div>
          )}

          {discussionId && (detailLoading || generating) && (
            <div className="space-y-4">
              <LoadingSkeleton variant="avatar" count={5} />
            </div>
          )}

          {displayGuests.length > 0 && (
            <div className="space-y-4">
              {/* Host card */}
              {displayGuests
                .filter((g) => g.role === 'host')
                .map((guest) => (
                  <GuestCard
                    key={guest.id}
                    guest={guest}
                    isHighlighted
                  />
                ))}

              {/* Expert grid */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {displayGuests
                  .filter((g) => g.role === 'guest')
                  .map((guest) => (
                    <GuestCard key={guest.id} guest={guest} />
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
