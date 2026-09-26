'use client'

import Link from 'next/link'
import { useState } from 'react'
import { IconArrowRight, IconCheck, IconSparkles, IconUserCircle } from '@tabler/icons-react'
import { useSession } from '@/components/session-provider'

export function PublicNav() {
  const { session, isLoading } = useSession()
  return (
    <header className="casepilot-nav-surface border-t-[3px] border-[#374151]">
      <nav className="mx-auto flex min-h-[82px] max-w-[1180px] items-center justify-between gap-4 px-5 sm:px-8">
        <Link href="/" className="flex items-center gap-2.5" aria-label="CasePilot home">
          <span className="grid size-9 place-items-center rounded-xl bg-[#111111] text-white"><IconSparkles className="size-[17px]" /></span>
          <span><span className="block font-brand text-[18px] font-bold tracking-[-.03em] text-[#111111]">CasePilot <span className="text-[#2563EB]">AI</span></span><span className="block text-[10px] font-semibold uppercase tracking-[.18em] text-[#64748B]">AI workroom</span></span>
        </Link>
        <div className="flex items-center gap-2 sm:gap-3">{!isLoading && session ? <><Link href="/dashboard" className="rounded-xl px-3 py-2 text-sm font-semibold text-[#525252] hover:bg-white hover:text-[#111111]">Dashboard</Link><Link href="/profile" className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-[#111111] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]"><IconUserCircle className="size-4" />Profile</Link></> : <><Link href="/signin" className="rounded-xl px-3 py-2 text-sm font-semibold text-[#525252] hover:bg-white hover:text-[#111111]">Sign in</Link><Link href="/signup" className="inline-flex min-h-10 items-center rounded-xl bg-[#111111] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]">Get started</Link></>}</div>
      </nav>
    </header>
  )
}

export function LandingPage() {
  const { session, isLoading } = useSession()
  const primaryHref = !isLoading && session ? '/dashboard' : '/signup'
  const secondaryHref = !isLoading && session ? '/profile' : '/signin'
  const primaryLabel = !isLoading && session ? 'Open dashboard' : 'Create your workspace'
  const secondaryLabel = !isLoading && session ? 'View profile' : 'View demo workspace'
  return (
    <div className="min-h-screen bg-[#FAFAFA] text-[#111111]"><PublicNav /><main>
      <section className="relative isolate overflow-hidden border-b border-[#D9C8B8] bg-[#F6F0E9]">
        <div aria-hidden="true" className="absolute inset-0 -z-20 bg-cover bg-center" style={{ backgroundImage: "url('https://hebbkx1anhila5yf.public.blob.vercel-storage.com/image-oPTh5nt25GNV5YZlb0h2Lz8FyjVs24.png')" }} />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,rgba(250,247,243,.88)_0%,rgba(250,247,243,.78)_43%,rgba(250,247,243,.54)_72%,rgba(250,247,243,.38)_100%)]" />
        <div aria-hidden="true" className="absolute inset-0 -z-10 bg-[#F7F1E9]/25 mix-blend-screen" />
        <div className="relative mx-auto grid max-w-[1180px] gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:py-28">
          <div><p className="text-xs font-bold uppercase tracking-[.16em] text-[#1D4ED8]">Evidence-first case preparation</p><h1 className="mt-5 max-w-3xl font-brand text-5xl font-bold leading-[1.04] tracking-[-.055em] text-[#172033] sm:text-7xl">Turn case material into a <span className="text-[#1D4ED8]">clear next step.</span></h1><p className="mt-6 max-w-xl text-lg leading-8 text-[#334155]">CasePilot brings documents, timelines, conflicts, and review tasks into one source-linked workspace for legal teams.</p><div className="mt-8 flex flex-wrap gap-3"><Link href={primaryHref} className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-[#111827] px-5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(17,24,39,.18)] hover:bg-[#1D4ED8]">{primaryLabel} <IconArrowRight data-icon="inline-end" /></Link><Link href={secondaryHref} className="inline-flex min-h-12 items-center rounded-xl border border-[#BFC7D4] bg-white/90 px-5 text-sm font-semibold text-[#111827] shadow-sm hover:bg-white">{secondaryLabel}</Link></div></div>
          <div className="rounded-[28px] border border-white/75 bg-white/95 p-5 shadow-[0_22px_60px_rgba(15,23,42,.18)] backdrop-blur-sm sm:p-7"><div className="flex items-center justify-between border-b border-[#EEF1F5] pb-5"><div><p className="font-mono text-xs font-bold text-[#525252]">PROP-001</p><h2 className="mt-1 font-brand text-xl font-bold">Rao v Mehta</h2></div><span className="rounded-full border border-[#FDE68A] bg-[#FFFBEB] px-3 py-1 text-xs font-semibold text-[#92400E]">Review</span></div><div className="mt-6 flex flex-col gap-3"><div className="rounded-xl bg-[#F8FBFF] p-4"><p className="text-xs font-bold uppercase tracking-[.1em] text-[#2563EB]">AI summary</p><p className="mt-2 text-sm leading-6 text-[#262626]">Payment is supported by the uploaded records. Possession remains for lawyer review.</p></div>{['Payment receipt verified','Timeline ready for review','2 potential conflicts flagged'].map((item) => <div key={item} className="flex items-center gap-3 rounded-xl border border-[#EEF1F5] bg-white p-3 text-sm font-semibold text-[#262626]"><IconCheck className="size-4 text-[#2563EB]" />{item}</div>)}</div></div>
        </div>
      </section>
      <section className="mx-auto grid max-w-[1180px] gap-8 px-5 py-16 sm:px-8 md:grid-cols-3"><Feature title="Source-linked" text="Keep every summary connected to the underlying record." /><Feature title="Review-ready" text="Move from raw evidence to clear, accountable decisions." /><Feature title="Team-focused" text="Give legal teams one calm place to prepare together." /></section>
    </main></div>
  )
}

function Feature({ title, text }: { title: string; text: string }) { return <article><div className="mb-4 size-2 rounded-full bg-[#2563EB]" /><h2 className="font-brand text-xl font-bold text-[#111111]">{title}</h2><p className="mt-2 text-sm leading-6 text-[#525252]">{text}</p></article> }

export function AuthPage({ mode }: { mode: 'signin' | 'signup' }) {
  const signup = mode === 'signup'; const [submitted, setSubmitted] = useState(false)
  return <div className="min-h-screen bg-[#F7F8FA]"><PublicNav /><main className="mx-auto max-w-[560px] px-5 py-14 sm:px-8"><section className="rounded-2xl border border-[#DDE3EC] bg-white p-7 shadow-sm"><p className="text-center text-xs font-bold uppercase tracking-[.12em] text-[#2563EB]">{signup ? 'Create your account' : 'Welcome back'}</p><h1 className="mt-2 text-center font-brand text-3xl font-bold text-[#111111]">{signup ? 'Start your workspace' : 'Sign in to CasePilot'}</h1><p className="mt-2 text-center text-sm text-[#525252]">{signup ? 'Begin reviewing evidence with your team.' : 'Continue to your evidence workspace.'}</p>{submitted ? <div className="mt-7 rounded-xl border border-[#BBF7D0] bg-[#F0FDF4] p-4 text-sm font-semibold text-[#166534]">Demo access ready. Continue to the workspace.</div> : <form className="mt-7 flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); setSubmitted(true) }}><label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">{signup ? 'Full name' : 'Email'}<input required type={signup ? 'text' : 'email'} className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111]" /></label>{signup && <label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">Work email<input required type="email" className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111]" /></label>}<label className="flex flex-col gap-2 text-sm font-semibold text-[#111111]">Password<input required type="password" className="h-11 rounded-xl border border-[#BFC7D4] px-3 text-[#111111]" /></label><button className="min-h-11 rounded-xl bg-[#111827] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]">{signup ? 'Create account' : 'Sign in'}</button></form>}{submitted && <Link href="/dashboard" className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-[#111827] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]">Continue to workspace</Link>}<p className="mt-6 text-center text-sm text-[#525252]">{signup ? 'Already have an account?' : 'New to CasePilot?'} <Link href={signup ? '/signin' : '/signup'} className="font-semibold text-[#1D4ED8] underline-offset-4 hover:underline">{signup ? 'Sign in' : 'Create an account'}</Link></p></section></main></div>
}

function profileName(session: ReturnType<typeof useSession>['session']) {
  const metadataName = session?.user.user_metadata?.display_name
  if (typeof metadataName === 'string' && metadataName.trim()) return metadataName.trim()
  return session?.user.email?.split('@')[0] || 'CasePilot user'
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'CP'
}

export function ProfilePage() {
  const { session, isLoading } = useSession()
  const name = profileName(session)
  const email = session?.user.email || 'No email address available'

  return <div className="min-h-screen bg-[#FAFAFA]"><PublicNav /><main className="mx-auto max-w-[920px] px-5 py-12 sm:px-8"><p className="text-xs font-bold uppercase tracking-[.14em] text-[#2563EB]">Account</p><h1 className="mt-2 font-brand text-4xl font-bold tracking-[-.04em] text-[#111111]">Your profile</h1><section className="mt-8 rounded-2xl border border-[#DDE3EC] bg-white p-6">{isLoading ? <p className="text-sm text-[#525252]">Loading your account…</p> : !session ? <><h2 className="font-brand text-xl font-bold text-[#111111]">Sign in to view your profile</h2><p className="mt-2 text-sm text-[#525252]">Your CasePilot account details are available after you sign in.</p><Link href="/signin" className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-[#111827] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]">Sign in</Link></> : <><div className="flex items-center gap-4"><span className="grid size-16 place-items-center rounded-full border border-[#C7D9EA] bg-[#E5F0FA] text-lg font-semibold text-[#24527D]">{initials(name)}</span><div><h2 className="font-brand text-xl font-bold text-[#111111]">{name}</h2><p className="text-sm text-[#525252]">{email}</p></div></div><div className="mt-7 grid gap-4 sm:grid-cols-2"><ProfileField label="Full name" value={name} /><ProfileField label="Email" value={email} /></div><div className="mt-7 flex flex-wrap gap-3"><Link href="/dashboard" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#111827] px-4 text-sm font-semibold text-white hover:bg-[#2563EB]">Open workspace <IconArrowRight data-icon="inline-end" /></Link><Link href="/" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#BFC7D4] px-4 text-sm font-semibold text-[#111827]"><IconUserCircle data-icon="inline-start" />Back home</Link></div></>}</section></main></div>
}

export default LandingPage

export function ProfileField({ label, value }: { label: string; value: string }) { return <div className="flex flex-col gap-2"><span className="text-xs font-bold uppercase tracking-[.1em] text-[#525252]">{label}</span><div className="rounded-xl border border-[#DDE3EC] bg-[#F8FAFD] px-4 py-3 text-sm font-semibold text-[#111111]">{value}</div></div> }
 const unused = null
 void unused
