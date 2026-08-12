import { createContext, useContext, useRef } from 'react';
import { create, type StoreApi, type UseBoundStore } from 'zustand';
import type {
  Discussion,
  Guest,
  Speech,
  Consensus,
  Divergence,
} from '../types';

// ─── State Shape ────────────────────────────────────────────────

export interface DiscussionState {
  // Data
  discussion: Discussion | null;
  guests: Guest[];
  speeches: Speech[];
  consensusList: Consensus[];
  divergenceList: Divergence[];

  // Connection
  isConnected: boolean;
  isEnded: boolean;
  error: string | null;

  // Derived / indexed
  agentStates: Record<string, string>;
  guestMap: Record<string, Guest>;

  // Actions
  setDiscussion: (discussion: Discussion) => void;
  setGuests: (guests: Guest[]) => void;
  addSpeech: (speech: Speech, roundNumber: number) => void;
  updateGuestState: (guestId: string, agentState: string) => void;
  addConsensus: (consensus: Consensus) => void;
  addDivergence: (divergence: Divergence) => void;
  setConnected: (connected: boolean) => void;
  setEnded: (consensusList: Consensus[], divergenceList: Divergence[]) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

// ─── Initial State ──────────────────────────────────────────────

const initialState = {
  discussion: null,
  guests: [],
  speeches: [],
  consensusList: [],
  divergenceList: [],
  isConnected: false,
  isEnded: false,
  error: null,
  agentStates: {},
  guestMap: {},
};

// ─── Store Factory ──────────────────────────────────────────────

export function createDiscussionStore(): UseBoundStore<StoreApi<DiscussionState>> {
  return create<DiscussionState>((set) => ({
    ...initialState,

    setDiscussion: (discussion) => set({ discussion }),

    setGuests: (guests) =>
      set({
        guests,
        guestMap: Object.fromEntries(guests.map((g) => [g.id, g])),
        agentStates: Object.fromEntries(
          guests.map((g) => [g.id, g.agent_state]),
        ),
      }),

    addSpeech: (speech, roundNumber) =>
      set((state) => ({
        speeches: [...state.speeches, speech],
        discussion: state.discussion
          ? { ...state.discussion, current_round: roundNumber }
          : null,
      })),

    updateGuestState: (guestId, agentState) =>
      set((state) => ({
        agentStates: { ...state.agentStates, [guestId]: agentState },
        guests: state.guests.map((g) =>
          g.id === guestId ? { ...g, agent_state: agentState as Guest['agent_state'] } : g,
        ),
        guestMap: {
          ...state.guestMap,
          [guestId]: state.guestMap[guestId]
            ? { ...state.guestMap[guestId], agent_state: agentState as Guest['agent_state'] }
            : state.guestMap[guestId],
        },
      })),

    addConsensus: (consensus) =>
      set((state) => ({
        consensusList: state.consensusList.some((c) => c.id === consensus.id)
          ? state.consensusList
          : [...state.consensusList, consensus],
      })),

    addDivergence: (divergence) =>
      set((state) => ({
        divergenceList: state.divergenceList.some((d) => d.id === divergence.id)
          ? state.divergenceList
          : [...state.divergenceList, divergence],
      })),

    setConnected: (connected) => set({ isConnected: connected }),

    setEnded: (consensusList, divergenceList) =>
      set((state) => ({
        isEnded: true,
        consensusList,
        divergenceList,
        discussion: state.discussion
          ? { ...state.discussion, status: 'ended' as const }
          : null,
      })),

    setError: (error) => set({ error }),

    reset: () => set({ ...initialState }),
  }));
}

// ─── Context Provider ───────────────────────────────────────────

type DiscussionStore = UseBoundStore<StoreApi<DiscussionState>>;

const DiscussionStoreContext = createContext<DiscussionStore | null>(null);

export function DiscussionStoreProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const storeRef = useRef<DiscussionStore>();
  if (!storeRef.current) {
    storeRef.current = createDiscussionStore();
  }
  return (
    <DiscussionStoreContext.Provider value={storeRef.current}>
      {children}
    </DiscussionStoreContext.Provider>
  );
}

export function useDiscussionStore<T>(
  selector: (state: DiscussionState) => T,
): T {
  const store = useContext(DiscussionStoreContext);
  if (!store) {
    throw new Error(
      'useDiscussionStore must be used within DiscussionStoreProvider',
    );
  }
  return store(selector);
}
