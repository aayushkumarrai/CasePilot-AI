# CasePilot AI — Design System

Source of truth for every screen. Reference this file in every Antigravity/Magic MCP
prompt so output stays visually consistent. Do not let any tool regenerate a palette
or type scale independently — extend this file instead.

---

## 1. Color Palette

Extracted from the existing landing page (Images 1–3). Treat hex values as
[best-approximation] — verify against the live build and adjust here first,
then propagate.

### Core
| Token | Hex | Usage |
|---|---|---|
| `--color-bg` | `#F8FAFC` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, panels, inspector background |
| `--color-border` | `#E2E8F0` | Card borders, dividers |
| `--color-text-primary` | `#0F172A` | Headlines, body copy |
| `--color-text-secondary` | `#64748B` | Subtext, captions, metadata labels |

### Brand / Accent
| Token | Hex | Usage |
|---|---|---|
| `--color-accent` | `#2563EB` | Primary CTA buttons, active nav link, links |
| `--color-accent-hover` | `#1D4ED8` | Button hover state |
| `--color-accent-light` | `#EFF6FF` | Badge backgrounds, highlighted panel fills |

### Semantic (status badges, conflict flags)
| Token | Hex | Usage |
|---|---|---|
| `--color-success` | `#16A34A` | "OCR Passed," "Audit Ready," verified states |
| `--color-success-bg` | `#F0FDF4` | Success badge background |
| `--color-warning` | `#D97706` | "Potential Conflict Detected" flags |
| `--color-warning-bg` | `#FFFBEB` | Warning panel background |
| `--color-danger` | `#DC2626` | Rejected states, hard errors |

**Rule:** never introduce a new color outside this table. If a screen needs one,
add it here first, with a named token — not inline as a raw hex value in code.

---

## 2. Typography

| Role | Font | Weight | Notes |
|---|---|---|---|
| Headings | Inter (or system sans fallback) | 600–700 | Tight tracking on H1/H2 |
| Body | Inter | 400–500 | 16px base, 1.5 line-height |
| Technical/mono labels | JetBrains Mono or IBM Plex Mono | 500 | Used for badges, Bates numbers, docket IDs, status tags — this is what gives the "legal-engineering" credibility feel. Keep it exclusive to labels, never body copy. |

Scale: `12px` (mono labels) / `14px` (body small) / `16px` (body) / `20px` (h3) /
`28px` (h2) / `40px` (h1, hero only).

---

## 3. Spacing & Layout

- Base unit: `4px`. All padding/margin values are multiples of 4 (8, 12, 16, 24, 32, 48, 64).
- Max content width: `1200px`, centered, `24px` side padding on mobile.
- Card padding: `24px` desktop / `16px` mobile.
- Section vertical rhythm: `80–120px` between major landing-page sections.

---

## 4. Components

### Buttons
- Primary: `--color-accent` bg, white text, `8px` border-radius, `12px 24px` padding.
- Secondary: white bg, `1px solid --color-border`, dark text, same radius/padding.
- Hover: primary darkens to `--color-accent-hover`; secondary gets `--color-bg` fill.

### Badges (pill labels)
- `4px` border-radius (near-square, not fully rounded — matches your screenshots).
- Mono font, uppercase, `11px`, letter-spacing `0.05em`.
- Background/text pairs from the semantic table above (e.g. success badge = `--color-success-bg` bg + `--color-success` text).

### Cards
- White surface, `1px solid --color-border`, `8px` border-radius, subtle shadow only on hover/interactive cards (`0 1px 3px rgba(0,0,0,0.06)`).

### Navigation
- Fixed top bar, white bg, `1px` bottom border, logo left, links center-left, auth actions right.
- Active link: `--color-accent` with underline.

---

## 5. Landing Page → Auth Flow (today's build scope)

Sections, top to bottom:

1. **Nav bar** — logo, Product/How it Works/Security/Enterprise links, "Log In" (text link) + "Request Demo" or "**Sign Up**" (primary button, top right).
2. **Hero** — eyebrow badge (mono, small), H1, subhead, two CTAs: primary → **Sign Up**, secondary → "See how it works."
3. **Product demo panel** — existing ingestion/chronology visual, unchanged.
4. **Process steps** (5-step row) — unchanged.
5. **Inspector demo** — unchanged.
6. **Governance section** — unchanged.
7. **Final CTA band** — restate value prop, primary button → **Sign Up**, secondary → "Schedule Demo."
8. **Footer** — minimal: logo, links, copyright.

### Auth screens (Sign Up / Log In)
- Centered single-column card, max-width `420px`, on `--color-bg` background.
- Logo above form.
- Form fields: label above input, `1px solid --color-border`, `8px` radius, focus state = `--color-accent` border.
- Primary button full-width inside card.
- Toggle link below card ("Already have an account? Log in" / "New here? Sign up").
- No sidebar, no marketing copy on this screen — keep it distraction-free, which itself signals "premium" more than decoration would.

---

## 6. Reserved for later (do not build yet, keep placeholders consistent)

When you build Brief / Timeline / Issues / Tasks screens, they inherit sections
1–4 of this file unchanged. Only new component patterns (timeline nodes, conflict
diff viewer, task approval cards) get added here — appended, not overwritten —
once you reach that stage.
