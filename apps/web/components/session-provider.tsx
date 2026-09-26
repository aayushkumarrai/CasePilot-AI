'use client'

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import type { Session } from '@supabase/supabase-js'
import { getSupabaseBrowserClient } from '@/lib/supabase'

type SessionContextValue = { session: Session | null; isLoading: boolean; signOut: () => Promise<void> }
const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const [session, setSession] = useState<Session | null>(null); const [isLoading, setIsLoading] = useState(true)
  const signOut = useCallback(async () => { try { await getSupabaseBrowserClient().auth.signOut() } finally { setSession(null); router.replace('/signin'); router.refresh() } }, [router])
  useEffect(() => {
    let active = true; let unsubscribe: (() => void) | undefined
    try { const supabase = getSupabaseBrowserClient(); supabase.auth.getSession().then(({ data }) => { if (active) { setSession(data.session); setIsLoading(false) } }); unsubscribe = supabase.auth.onAuthStateChange((_event, nextSession) => { if (active) setSession(nextSession) }).data.subscription.unsubscribe } catch { if (active) setIsLoading(false) }
    return () => { active = false; unsubscribe?.() }
  }, [])
  useEffect(() => { const handleUnauthorized = () => void signOut(); window.addEventListener('casepilot:unauthorized', handleUnauthorized); return () => window.removeEventListener('casepilot:unauthorized', handleUnauthorized) }, [signOut])
  const value = useMemo(() => ({ session, isLoading, signOut }), [session, isLoading, signOut])
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession() { const value = useContext(SessionContext); if (!value) throw new Error('useSession must be used inside SessionProvider'); return value }
export function RequireSession({ children }: { children: React.ReactNode }) { const { session, isLoading } = useSession(); const router = useRouter(); useEffect(() => { if (!isLoading && !session) router.replace('/signin') }, [isLoading, router, session]); if (isLoading || !session) return <main className="grid min-h-screen place-items-center text-sm text-[#525252]">Loading your workspace…</main>; return <>{children}</> }
