import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useDiscussionStream } from '../hooks/useDiscussionStream';
import {
  DiscussionStoreProvider,
  useDiscussionStore,
} from '../store/useDiscussionStore';
import { api, ApiError } from '../lib/api';
import type {
  DiscussionDetail,
  Speech,
  Consensus,
  Divergence,
} from '../types';
import StudioHeader from '../components/StudioHeader';
import GuestStatusWindow from '../components/GuestStatusWindow';
import TranscriptItem from '../components/TranscriptItem';
import ConsensusTag from '../components/ConsensusTag';
import DivergenceCard from '../components/DivergenceCard';
import LoadingSkeleton from '../components/LoadingSkeleton';

// ─── Inner Component (has store context access) ─────────────────

function StudioPageInner() {
  const { discussionId } = useParams<{ discussionId: string }>();

  // Local states
  const [ending, setEnding] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Store selectors
  const discussion = useDiscussionStore((s) => s.discussion);
  const guests = useDiscussionStore((s) => s.guests);
  const speeches = useDiscussionStore((s) => s.speeches);
  const consensusList = useDiscussionStore((s) => s.consensusList);
  const divergenceList = useDiscussionStore((s) => s.divergenceList);
  const guestMap = useDiscussionStore((s) => s.guestMap);
  const agentStates = useDiscussionStore((s) => s.agentStates);
  const isConnected = useDiscussionStore((s) => s.isConnected);
  const isEnded = useDiscussionStore((s) => s.isEnded);
  const error = useDiscussionStore((s) => s.error);

  const setDiscussion = useDiscussionStore((s) => s.setDiscussion);
  const setGuests = useDiscussionStore((s) => s.setGuests);
  const addSpeech = useDiscussionStore((s) => s.addSpeech);
  const updateGuestState = useDiscussionStore((s) => s.updateGuestState);
  const addConsensus = useDiscussionStore((s) => s.addConsensus);
  const addDivergence = useDiscussionStore((s) => s.addDivergence);
  const setConnected = useDiscussionStore((s) => s.setConnected);
  const setEnded = useDiscussionStore((s) => s.setEnded);
  const setError = useDiscussionStore((s) => s.setError);

  // Fetch discussion detail
  const {
    data: detail,
    error: fetchError,
    loading,
  } = useApi<DiscussionDetail>(
    () => api.getDiscussion(discussionId!),
    [discussionId],
  );

  // Populate store from fetched detail
  useEffect(() => {
    if (!detail) return;
    const { guests: detailGuests, speeches: detailSpeeches, ...disc } = detail;
    setDiscussion(disc);

    if (detailGuests && detailGuests.length > 0) {
      setGuests(detailGuests);
    }

    // Add existing speeches one by one
    if (detailSpeeches && detailSpeeches.length > 0) {
      detailSpeeches.forEach((s) => {
        addSpeech(s, s.round_number);
      });
    }
  }, [detail]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch consensus/divergence for ended discussions
  useEffect(() => {
    if (!detail || detail.status !== 'ended') return;
    Promise.all([
      api.getConsensusList(discussionId!),
      api.getDivergenceList(discussionId!),
    ])
      .then(([consensus, divergence]) => {
        setEnded(consensus, divergence);
      })
      .catch(() => {
        // Non-critical, use empty arrays
        setEnded([], []);
      });
  }, [detail?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // SSE callbacks
  const streamCallbacks = useRef({
    onSpeech: (speech: Speech, roundNumber: number) => {
      addSpeech(speech, roundNumber);
    },
    onGuestStateChange: (guestId: string, state: string) => {
      updateGuestState(guestId, state);
    },
    onConsensus: (consensus: Consensus) => {
      addConsensus(consensus);
    },
    onDivergence: (divergence: Divergence) => {
      addDivergence(divergence);
    },
    onEnded: (consensusList: Consensus[], divergenceList: Divergence[]) => {
      setEnded(consensusList, divergenceList);
      setConnected(false);
    },
    onError: (message: string) => {
      setError(message);
      setToast(message);
      setTimeout(() => setToast(null), 5000);
    },
    onConnectionChange: (connected: boolean) => {
      setConnected(connected);
    },
  });

  // Open SSE for active discussions
  useDiscussionStream(
    discussionId!,
    !!(detail?.status === 'ended' || isEnded),
    streamCallbacks.current,
  );

  // End discussion
  const handleEndDiscussion = useCallback(async () => {
    if (!discussionId) return;
    setEnding(true);
    try {
      await api.endDiscussion(discussionId);
    } catch (err) {
      setToast(err instanceof ApiError ? err.message : '结束讨论失败');
      setTimeout(() => setToast(null), 5000);
    } finally {
      setEnding(false);
    }
  }, [discussionId]);

  // Auto-scroll logic
  const handleTranscriptScroll = useCallback(() => {
    const el = transcriptRef.current;
    if (!el) return;
    const bottomThreshold = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsAtBottom(bottomThreshold < 200);
  }, []);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el && isAtBottom) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }
  }, [speeches.length, isAtBottom]);

  const scrollToBottom = useCallback(() => {
    const el = transcriptRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      setIsAtBottom(true);
    }
  }, []);

  // Derive state
  const status = discussion?.status || detail?.status || 'ended';
  const isActive = status === 'active';
  const showEnded = status === 'ended' || isEnded;

  // Compute last speech per guest for thought summary
  const lastSpeechByGuest: Record<string, Speech> = {};
  for (let i = speeches.length - 1; i >= 0; i--) {
    const s = speeches[i];
    if (s.guest_id && !lastSpeechByGuest[s.guest_id]) {
      lastSpeechByGuest[s.guest_id] = s;
    }
    if (Object.keys(lastSpeechByGuest).length === guests.length) break;
  }

  // ─── Render ───────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex h-screen flex-col">
        <div className="flex-shrink-0 border-b border-studio-border bg-studio-card px-6 py-4">
          <div className="h-7 w-64 animate-pulse rounded bg-studio-border" />
        </div>
        <div className="flex flex-1 gap-0 overflow-hidden">
          <div className="hidden w-1/4 flex-shrink-0 space-y-3 overflow-y-auto border-r border-studio-border p-4 lg:block">
            <LoadingSkeleton variant="avatar" count={4} />
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <LoadingSkeleton variant="speech" count={3} />
          </div>
          <div className="hidden w-1/4 flex-shrink-0 space-y-4 overflow-y-auto border-l border-studio-border p-4 xl:block">
            <LoadingSkeleton variant="text" count={2} />
          </div>
        </div>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4">
        <span className="text-4xl">🔍</span>
        <p className="text-xl font-semibold text-white">讨论不存在</p>
        <p className="text-gray-400">{fetchError}</p>
        <Link
          to="/"
          className="rounded-lg border border-studio-border px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-studio-border/30"
        >
          返回首页
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Toast notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 animate-slide-in rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 shadow-lg backdrop-blur">
          {toast}
        </div>
      )}

      {/* Header */}
      <StudioHeader
        topic={detail?.topic || discussion?.topic || ''}
        currentRound={discussion?.current_round || detail?.current_round || 0}
        maxRounds={discussion?.max_rounds || detail?.max_rounds || 0}
        status={status}
        isConnected={isConnected}
        onEndDiscussion={handleEndDiscussion}
        isLoading={ending}
      />

      {/* Three-column body */}
      <div className="flex flex-1 overflow-hidden">
        {/* ─── Left: Guest Windows (25%) ─── */}
        <aside className="hidden w-1/4 flex-shrink-0 flex-col gap-3 overflow-y-auto border-r border-studio-border p-4 lg:flex 2xl:w-1/5">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">
            嘉宾
          </h3>

          {/* Host first */}
          {guests
            .filter((g) => g.role === 'host')
            .map((g) => (
              <GuestStatusWindow
                key={g.id}
                guest={g}
                agentState={agentStates[g.id] || g.agent_state}
                lastSpeech={lastSpeechByGuest[g.id]}
              />
            ))}

          {/* Then experts */}
          {guests
            .filter((g) => g.role === 'guest')
            .map((g) => (
              <GuestStatusWindow
                key={g.id}
                guest={g}
                agentState={agentStates[g.id] || g.agent_state}
                lastSpeech={lastSpeechByGuest[g.id]}
              />
            ))}

          {guests.length === 0 && (
            <p className="text-sm text-gray-600">暂无嘉宾</p>
          )}
        </aside>

        {/* ─── Center: Transcript (50%) ─── */}
        <main
          ref={transcriptRef}
          onScroll={handleTranscriptScroll}
          data-testid="transcript-area"
          className="flex flex-1 flex-col gap-4 overflow-y-auto p-6 lg:w-1/2 2xl:w-[55%]"
        >
          {/* Disconnected banner */}
          {isActive && !isConnected && (
            <div className="flex-shrink-0 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-400 animate-fade-in">
              ⚠️ 连接中断，正在重连...
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="flex-shrink-0 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400 animate-fade-in">
              {error}
            </div>
          )}

          {/* Speeches */}
          {speeches.length === 0 && isActive && (
            <div className="flex flex-1 flex-col items-center justify-center text-gray-500">
              <span className="text-4xl mb-3">🎬</span>
              <p>讨论即将开始...</p>
              {!isConnected && (
                <p className="text-sm mt-2 text-yellow-400">
                  等待连接恢复
                </p>
              )}
            </div>
          )}

          {speeches.map((speech, index) => (
            <TranscriptItem
              key={speech.id}
              speech={speech}
              guest={speech.guest_id ? guestMap[speech.guest_id] : undefined}
              isLatest={index === speeches.length - 1}
              index={index}
            />
          ))}

          {/* Hero summary for ended state */}
          {showEnded && !isActive && (
            <div className="mt-4 animate-fade-in">
              <div className="rounded-xl border border-studio-accent/30 bg-studio-accent/5 p-6 text-center">
                <span className="text-4xl">🎉</span>
                <h2 className="mt-3 text-xl font-bold text-white">
                  讨论已结束
                </h2>
                <p className="mt-1 text-gray-400">
                  共 {speeches.length} 条发言
                  {discussion?.max_rounds ? ` · ${discussion.max_rounds} 轮讨论` : ''}
                </p>
                <Link
                  to="/"
                  className="mt-4 inline-block rounded-lg border border-studio-border px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-studio-border/30"
                >
                  返回首页
                </Link>
              </div>
            </div>
          )}

          {/* Scroll-to-bottom button */}
          {!isAtBottom && speeches.length > 0 && (
            <button
              onClick={scrollToBottom}
              className="sticky bottom-4 mx-auto flex-shrink-0 rounded-full border border-studio-accent/50 bg-studio-accent/10 px-4 py-2 text-sm text-studio-accent transition-colors hover:bg-studio-accent/20"
            >
              ↓ 新消息
            </button>
          )}
        </main>

        {/* ─── Right: Consensus & Divergence (25%) ─── */}
        <aside className="hidden w-1/4 flex-shrink-0 flex-col gap-4 overflow-y-auto border-l border-studio-border p-4 xl:flex 2xl:w-[20%]">
          {/* Consensus */}
          <div data-testid="consensus-area">
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              <span>✅</span> 共识
            </h3>
            {consensusList.length === 0 && (
              <p className="text-sm text-gray-600">暂无共识</p>
            )}
            <div className="space-y-3">
              {consensusList.map((c) => (
                <ConsensusTag
                  key={c.id}
                  consensus={c}
                  guestMap={guestMap}
                />
              ))}
            </div>
          </div>

          {/* Divergence */}
          <div data-testid="divergence-area">
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              <span>❌</span> 分歧
            </h3>
            {divergenceList.length === 0 && (
              <p className="text-sm text-gray-600">暂无分歧</p>
            )}
            <div className="space-y-3">
              {divergenceList.map((d) => (
                <DivergenceCard
                  key={d.id}
                  divergence={d}
                  guestMap={guestMap}
                />
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* ─── Mobile: Consensus/Divergence accordion (<768px) ─── */}
      <div className="block border-t border-studio-border p-4 xl:hidden">
        <MobileInsightsAccordion
          consensusList={consensusList}
          divergenceList={divergenceList}
          guestMap={guestMap}
        />
      </div>

      {/* ─── Tablet: Guest accordion (<1024px) ─── */}
      <div className="block border-t border-studio-border p-4 lg:hidden">
        <MobileGuestsAccordion
          guests={guests}
          agentStates={agentStates}
          lastSpeechByGuest={lastSpeechByGuest}
        />
      </div>
    </div>
  );
}

// ─── Mobile sub-components ─────────────────────────────────────

function MobileGuestsAccordion({
  guests,
  agentStates,
  lastSpeechByGuest,
}: {
  guests: import('../types').Guest[];
  agentStates: Record<string, string>;
  lastSpeechByGuest: Record<string, import('../types').Speech>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-sm font-semibold text-white"
      >
        <span>🎭 嘉宾 ({guests.length})</span>
        <span className="text-gray-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          {guests.map((g) => (
            <GuestStatusWindow
              key={g.id}
              guest={g}
              agentState={agentStates[g.id] || g.agent_state}
              lastSpeech={lastSpeechByGuest[g.id]}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MobileInsightsAccordion({
  consensusList,
  divergenceList,
  guestMap,
}: {
  consensusList: Consensus[];
  divergenceList: Divergence[];
  guestMap: Record<string, import('../types').Guest>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-sm font-semibold text-white"
      >
        <span>
          💡 共识 ({consensusList.length}) · 分歧 ({divergenceList.length})
        </span>
        <span className="text-gray-500">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          {consensusList.map((c) => (
            <ConsensusTag key={c.id} consensus={c} guestMap={guestMap} />
          ))}
          {divergenceList.map((d) => (
            <DivergenceCard key={d.id} divergence={d} guestMap={guestMap} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Wrapper with Store Provider ────────────────────────────────

export default function StudioPage() {
  return (
    <DiscussionStoreProvider>
      <StudioPageInner />
    </DiscussionStoreProvider>
  );
}
