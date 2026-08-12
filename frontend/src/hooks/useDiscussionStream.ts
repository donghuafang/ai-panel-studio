import { useEffect, useRef } from 'react';
import type {
  Speech,
  Consensus,
  Divergence,
  SpeechEvent,
  GuestStateEvent,
  ConsensusEvent,
  DivergenceEvent,
  DiscussionEndedEvent,
  ErrorEvent,
} from '../types';

interface UseDiscussionStreamCallbacks {
  onSpeech: (speech: Speech, roundNumber: number) => void;
  onGuestStateChange: (guestId: string, state: string) => void;
  onConsensus: (consensus: Consensus) => void;
  onDivergence: (divergence: Divergence) => void;
  onEnded: (consensusList: Consensus[], divergenceList: Divergence[]) => void;
  onError: (message: string) => void;
  onConnectionChange: (connected: boolean) => void;
}

export function useDiscussionStream(
  discussionId: string,
  isEnded: boolean,
  callbacks: UseDiscussionStreamCallbacks,
) {
  // Use refs for callbacks to avoid re-running the effect on every render
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const isEndedRef = useRef(isEnded);
  isEndedRef.current = isEnded;

  useEffect(() => {
    if (isEnded) return;

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
    const url = `${baseUrl}/api/discussions/${discussionId}/stream`;

    let eventSource: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    let shouldReconnect = true;

    const resetHeartbeat = () => {
      if (heartbeatTimeout) clearTimeout(heartbeatTimeout);
      heartbeatTimeout = setTimeout(() => {
        eventSource?.close();
      }, 45_000);
    };

    const connect = () => {
      eventSource = new EventSource(url);
      resetHeartbeat();

      eventSource.addEventListener('speech_added', (e: MessageEvent) => {
        const data: SpeechEvent = JSON.parse(e.data);
        callbacksRef.current.onSpeech(data.speech, data.round_number);
      });

      eventSource.addEventListener('guest_state_changed', (e: MessageEvent) => {
        const data: GuestStateEvent = JSON.parse(e.data);
        callbacksRef.current.onGuestStateChange(data.guest_id, data.agent_state);
      });

      eventSource.addEventListener('consensus_updated', (e: MessageEvent) => {
        const data: ConsensusEvent = JSON.parse(e.data);
        callbacksRef.current.onConsensus(data.consensus);
      });

      eventSource.addEventListener('divergence_updated', (e: MessageEvent) => {
        const data: DivergenceEvent = JSON.parse(e.data);
        callbacksRef.current.onDivergence(data.divergence);
      });

      eventSource.addEventListener('discussion_ended', (e: MessageEvent) => {
        const data: DiscussionEndedEvent = JSON.parse(e.data);
        callbacksRef.current.onEnded(
          data.final_consensus,
          data.final_divergence,
        );
        shouldReconnect = false;
        eventSource?.close();
      });

      eventSource.addEventListener('error', (e: MessageEvent) => {
        try {
          const data: ErrorEvent = JSON.parse(e.data);
          callbacksRef.current.onError(data.message);
        } catch {
          // Non-JSON error event — this is the transport error handler below
        }
      });

      eventSource.addEventListener('ping', () => {
        resetHeartbeat();
      });

      eventSource.onopen = () => {
        retryCount = 0;
        callbacksRef.current.onConnectionChange(true);
        resetHeartbeat();
      };

      eventSource.onerror = () => {
        callbacksRef.current.onConnectionChange(false);
        eventSource?.close();
        if (heartbeatTimeout) clearTimeout(heartbeatTimeout);

        if (shouldReconnect && !isEndedRef.current) {
          const delay =
            Math.min(1000 * Math.pow(2, retryCount), 30_000) +
            Math.random() * 1000;
          retryCount++;
          retryTimeout = setTimeout(connect, delay);
        }
      };
    };

    // Page visibility: close on hidden, reconnect on visible
    const handleVisibilityChange = () => {
      if (document.hidden) {
        eventSource?.close();
        if (retryTimeout) clearTimeout(retryTimeout);
      } else if (shouldReconnect && !isEndedRef.current) {
        retryCount = 0;
        connect();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Initial connection
    connect();

    return () => {
      shouldReconnect = false;
      if (retryTimeout) clearTimeout(retryTimeout);
      if (heartbeatTimeout) clearTimeout(heartbeatTimeout);
      eventSource?.close();
      document.removeEventListener(
        'visibilitychange',
        handleVisibilityChange,
      );
    };
  }, [discussionId, isEnded]);
}
