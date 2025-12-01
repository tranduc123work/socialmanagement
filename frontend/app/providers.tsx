'use client';

import { AuthProvider } from '@/contexts/AuthContext';
import { TaskProvider } from '@/contexts/TaskContext';
import { Toaster } from 'sonner';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <TaskProvider>
        {children}
        <Toaster position="top-right" richColors />
      </TaskProvider>
    </AuthProvider>
  );
}
