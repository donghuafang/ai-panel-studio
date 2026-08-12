import type { Divergence, Guest } from '../types';

interface DivergenceCardProps {
  divergence: Divergence;
  guestMap: Record<string, Guest>;
}

export default function DivergenceCard({
  divergence,
  guestMap,
}: DivergenceCardProps) {
  return (
    <div className="animate-fade-in rounded-xl border-l-4 border-l-red-500 bg-studio-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-lg">❌</span>
        <span className="text-sm font-medium text-red-400">分歧</span>
      </div>
      <p className="text-sm text-gray-200 leading-relaxed">
        {divergence.content}
      </p>
      {divergence.opposing_pairs.length > 0 && (
        <div className="mt-3 space-y-2">
          <span className="text-xs text-gray-500">对立观点：</span>
          {divergence.opposing_pairs.map((pair, i) => {
            const guestA = pair[0] ? guestMap[pair[0]] : null;
            const guestB = pair[1] ? guestMap[pair[1]] : null;
            return (
              <div
                key={i}
                className="flex items-center gap-2 text-xs"
              >
                <span
                  className="rounded px-2 py-1 font-medium text-white"
                  style={{
                    backgroundColor: (guestA?.color || '#6B7280') + '33',
                    color: guestA?.color || '#9CA3AF',
                  }}
                >
                  {guestA?.name || '未知'}
                </span>
                <span className="text-gray-500">VS</span>
                <span
                  className="rounded px-2 py-1 font-medium text-white"
                  style={{
                    backgroundColor: (guestB?.color || '#6B7280') + '33',
                    color: guestB?.color || '#9CA3AF',
                  }}
                >
                  {guestB?.name || '未知'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
