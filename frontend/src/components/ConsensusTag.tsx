import type { Consensus, Guest } from '../types';

interface ConsensusTagProps {
  consensus: Consensus;
  guestMap: Record<string, Guest>;
}

export default function ConsensusTag({ consensus, guestMap }: ConsensusTagProps) {
  const supporters = consensus.supporter_guest_ids
    .map((id) => guestMap[id])
    .filter(Boolean);

  return (
    <div className="animate-fade-in rounded-xl border-l-4 border-l-green-500 bg-studio-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-lg">✅</span>
        <span className="text-sm font-medium text-green-400">共识</span>
      </div>
      <p className="text-sm text-gray-200 leading-relaxed">
        {consensus.content}
      </p>
      {supporters.length > 0 && (
        <div className="mt-3 flex items-center gap-2">
          <span className="text-xs text-gray-500">支持者：</span>
          <div className="flex -space-x-2">
            {supporters.map((guest) => (
              <span
                key={guest.id}
                className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white ring-2 ring-studio-card"
                style={{ backgroundColor: guest.color }}
                title={guest.name}
              >
                {guest.name.charAt(0)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
