import type { Guest } from '../types';

interface GuestCardProps {
  guest: Guest;
  isHighlighted?: boolean;
}

export default function GuestCard({ guest, isHighlighted }: GuestCardProps) {
  return (
    <div
      data-testid="guest-card"
      className={`relative overflow-hidden rounded-xl border bg-studio-card p-4 transition-all ${
        isHighlighted
          ? 'border-studio-gold/50 shadow-md shadow-studio-gold/10'
          : 'border-studio-border'
      }`}
    >
      {/* Left color bar */}
      <div
        className="absolute left-0 top-0 h-full w-1"
        style={{ backgroundColor: guest.color }}
      />

      <div className="flex items-start gap-3 pl-2">
        {/* Avatar */}
        <div
          className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full text-lg font-bold text-white"
          style={{ backgroundColor: guest.color + '33' }}
        >
          {guest.name.charAt(0)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-white truncate">{guest.name}</h4>
            {isHighlighted && (
              <span className="flex-shrink-0 rounded-full border border-studio-gold/50 bg-studio-gold/10 px-2 py-0.5 text-xs text-studio-gold">
                主持人
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400">
            {guest.profession}
            {guest.title ? ` · ${guest.title}` : ''}
          </p>
          <p className="mt-1 text-xs text-gray-500 line-clamp-3">
            {guest.stance}
          </p>
        </div>
      </div>
    </div>
  );
}
