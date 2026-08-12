import { useState } from 'react';

interface StudioHeaderProps {
  topic: string;
  currentRound: number;
  maxRounds: number;
  status: string;
  isConnected: boolean;
  onEndDiscussion: () => void;
  isLoading?: boolean;
}

export default function StudioHeader({
  topic,
  currentRound,
  maxRounds,
  status,
  isConnected,
  onEndDiscussion,
  isLoading = false,
}: StudioHeaderProps) {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleEndClick = () => {
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    setShowConfirm(false);
    onEndDiscussion();
  };

  return (
    <>
      <header className="spotlight-bg flex flex-shrink-0 items-center justify-between border-b border-studio-border bg-studio-card/80 px-6 py-4 backdrop-blur">
        <div className="flex min-w-0 items-center gap-4">
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-7 w-64 animate-pulse rounded bg-studio-border" />
              <div className="h-4 w-20 animate-pulse rounded bg-studio-border" />
            </div>
          ) : (
            <>
              <h1 className="truncate text-lg font-bold text-white" title={topic}>
                {topic}
              </h1>
              {status === 'active' && (
                <span className="flex-shrink-0 rounded-full border border-studio-accent/30 bg-studio-accent/10 px-3 py-1 text-sm font-medium text-studio-accent">
                  第 {currentRound}/{maxRounds} 轮
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Connection indicator */}
          <span className="flex items-center gap-1.5 text-xs text-gray-400">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-400' : 'bg-red-400'
              }`}
            />
            {isConnected ? '已连接' : '未连接'}
          </span>

          {/* End discussion button */}
          {status === 'active' && (
            <button
              onClick={handleEndClick}
              disabled={isLoading}
              data-testid="end-discussion-btn"
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-50"
            >
              结束讨论
            </button>
          )}
        </div>
      </header>

      {/* Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-studio-border bg-studio-card p-6 shadow-2xl animate-fade-in">
            <h3 className="text-lg font-semibold text-white mb-2">
              确定要结束当前讨论吗？
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              结束后将无法继续发言，但可以查看完整的讨论记录。
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="rounded-lg border border-studio-border px-4 py-2 text-sm text-gray-300 transition-colors hover:bg-studio-border/30"
              >
                取消
              </button>
              <button
                onClick={handleConfirm}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                确认结束
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
