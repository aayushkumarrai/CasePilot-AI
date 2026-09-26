'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FormEvent, useEffect, useState } from 'react'

import { PublicNav } from '@/components/casepilot-public'
import { getSupabaseBrowserClient } from '@/lib/supabase'
import { useSession } from '@/components/session-provider'

type AuthMode = 'signin' | 'signup'

type AuthPageProps = {
  mode: AuthMode
}

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

export function AuthPage({ mode }: AuthPageProps) {
  const router = useRouter()
  const { session, isLoading: isSessionLoading } = useSession()
  const isSignUp = mode === 'signup'
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!isSessionLoading && session) router.replace('/dashboard')
  }, [isSessionLoading, router, session])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setNotice(null)
    setIsSubmitting(true)

    try {
      const supabase = getSupabaseBrowserClient()
      const result = isSignUp
        ? await supabase.auth.signUp({
            email: email.trim(),
            password,
            options: { data: { display_name: displayName.trim() || undefined } },
          })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password })

      if (result.error) {
        setError(result.error.message)
        return
      }

      if (result.data.session) {
        router.replace('/dashboard')
        return
      }

      setNotice('Check your email to confirm your account, then sign in.')
    } catch (caughtError) {
      setError(messageFrom(caughtError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      <PublicNav />
      <main className="mx-auto max-w-[560px] px-5 py-14 sm:px-8">
        <section className="rounded-2xl border border-[#DDE3EC] bg-white p-7 shadow-sm">
          <p className="text-center text-xs font-bold uppercase tracking-[.12em] text-[#2563EB]">
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </p>
          <h1 className="mt-2 text-center font-brand text-3xl font-bold text-[#111111]">
            {isSignUp ? 'Start your workspace' : 'Sign in to CasePilot'}
          </h1>
          <p className="mt-2 text-center text-sm text-[#525252]">
            {isSignUp ? 'Begin reviewing evidence with your team.' : 'Continue to your evidence workspace.'}
          </p>

          <form className="mt-7 flex flex-col gap-4" onSubmit={handleSubmit}>
            {isSignUp && (
              <label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">
                Full name
                <input
                  required
                  autoComplete="name"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111] outline-none focus:ring-2 focus:ring-[#2563EB]"
                />
              </label>
            )}
            <label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">
              Email
              <input
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111] outline-none focus:ring-2 focus:ring-[#2563EB]"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">
              Password
              <input
                required
                type="password"
                minLength={6}
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111] outline-none focus:ring-2 focus:ring-[#2563EB]"
              />
            </label>

            {error && <p role="alert" className="rounded-xl border border-[#FECACA] bg-[#FEF2F2] p-3 text-sm text-[#991B1B]">{error}</p>}
            {notice && <p role="status" className="rounded-xl border border-[#BBF7D0] bg-[#F0FDF4] p-3 text-sm text-[#166534]">{notice}</p>}

            <button
              type="submit"
              disabled={isSubmitting}
              className="min-h-11 rounded-xl bg-[#111827] px-4 text-sm font-semibold text-white hover:bg-[#2563EB] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#525252]">
            {isSignUp ? 'Already have an account?' : 'New to CasePilot?'}{' '}
            <Link href={isSignUp ? '/signin' : '/signup'} className="font-semibold text-[#1D4ED8] underline-offset-4 hover:underline">
              {isSignUp ? 'Sign in' : 'Create an account'}
            </Link>
          </p>
        </section>
      </main>
    </div>
  )
}
