import React, { createContext, useContext, ReactNode } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface RealtimeContextType {
  isConnected: boolean;
  lastMessage: any;
  sendMessage: (type: string, data: any) => void;
  error: any;
}

const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { isConnected, lastMessage, sendMessage, error } = useWebSocket('/ws');

  const value = {
    isConnected,
    lastMessage,
    sendMessage,
    error,
  };

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (context === undefined) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }
  return context;
}