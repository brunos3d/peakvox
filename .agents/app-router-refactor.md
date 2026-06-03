# App Router Architecture Refactor — Audit, Spec & Plan

**Scope:** `frontend/` routing + layout system. **Constraint:** preserve UX/behavior exactly; improve architecture only.
**Baseline:** Next.js 16.2.7, React 19.2.7, App Router. 9 routes, all marked `"use client"`.

---

## Phase 1 — Architecture Audit

### Current composition

```
app/layout.tsx (Server)
└─ <Providers> (Client: QueryClientProvider)
   └─ <AppShell> (Client)              ← whole frame is a client component
      ├─ desktop <aside><AppSidebar/></aside>   (Client: usePathname + status polling)
      ├─ mobile <Sheet> + menu button           (Client: useState menuOpen)
      ├─ useVoices()                            (Client: data preload side-effect)
      ├─ <main>{children}</main>
      └─ <BottomPlayer/>                        (Client: job polling + playback)
```

Every page then re-composes the same frame-in-the-page:

```
page.tsx ("use client")
└─ <PageLayout> (Client: useState for mobile context-panel sheet)
   ├─ <PageHeader/> (Server-compatible, but pulled into client graph)
   └─ page content
```

### Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F1 | **All 9 pages are `"use client"`, but 4 have zero client logic** | High | `/clone`, `/settings`, `/api`, `/api/voices` only render child components + static JSX |
| F2 | **`PageLayout` is a client wrapper used even when no context panel exists** | High | 6 of 9 pages pass no `contextPanel`; they pay for the client sheet machinery for nothing |
| F3 | **`AppShell` frame is entirely client** though most of it is static markup | Medium | Only `menuOpen` + `useVoices()` truly need the client; the grid/`<main>`/`<aside>` are static |
| F4 | **`PageHeader` is already server-safe but always imported by client pages** | Low | No hooks; pure presentational — should render on the server |
| F5 | **No nested layouts** — the `/api` section repeats the same container wrapper in 4 files | Medium | Each API page wraps itself in `<PageLayout><div className="mx-auto max-w-Nxl">` |
| F6 | **`useVoices()` preload buried inside the shell frame** | Low | Couples a data side-effect to layout markup |

### Anti-patterns confirmed
- Client-by-default on route entry points (F1) — the App Router default is Server; `"use client"` should be opt-in at leaves.
- A custom client "layout component" (`PageLayout`) standing in for what nested `layout.tsx` + a server container should do (F2, F5).
- Layout markup and data-fetch side-effects fused into one client component (F3, F6).

### What must STAY client (correctly)
- `/` (TTS), `/history`, `/voices` — heavy local state, React Query, dialogs, event handlers.
- `/api/keys`, `/api/usage` — React Query reads/mutations.
- `AppSidebar` (active link via `usePathname`, live status polling), `BottomPlayer` (job polling), all dialogs/wizards/players, the mobile menu toggle, and the context-panel sheet toggle.

---

## Phase 2 — Refactoring Specification

### Decisions (with rationale)

**D1 — Server frame + client islands for `AppShell`.**
`AppShell` becomes a **Server Component** rendering the static grid. The genuinely interactive parts become small client islands:
- `MobileNav` (client) — mobile top bar + menu button + slide-over `Sheet` (owns `menuOpen`).
- `VoicesPreloader` (client) — calls `useVoices()`, renders `null` (data side-effect decoupled from markup).
- `AppSidebar`, `BottomPlayer` — already client, rendered as islands.

Valid because the root layout passes `AppShell` as **children** of the client `Providers`, so a Server `AppShell` is allowed, and `children` (pages) keep server-rendering.

**D2 — `PageContainer` (Server) replaces `PageLayout` for no-panel pages.**
New `PageContainer` reproduces *exactly* the DOM `PageLayout` emits when `contextPanel` is undefined:
`<div className="flex h-full min-h-0"><div className="flex-1 min-w-0 overflow-y-auto px-6 lg:px-10 py-8">{children}</div></div>`.
Zero client JS. Identical layout/scroll → identical UX.

**D3 — Native nested layout for the `/api` section.**
Add `app/api/layout.tsx` (Server) that renders `<PageContainer>`. The 4 API pages drop their wrapper and render only their `max-w` content. This is genuine App Router adoption (a real shared section layout) and removes container boilerplate from 4 files.

**D4 — Convert eligible pages to Server Components.**
Drop `"use client"` from `/clone`, `/settings`, `/api`, `/api/voices`. They render client islands (`VoiceWizard`, `SettingsPanel`, `CodeTabs`) as children — the React Server/Client boundary handles this natively. Verified server-safe: `getApiBaseUrl()` is a `process.env` constant; `api-examples.ts` uses no browser APIs.

**D5 — Keep `PageLayout` (client) for the 3 panel pages.** `/`, `/history`, `/voices` keep it. The context panels for `/history` and `/voices` are **stateful extensions of the page** (filter chips drive the list; selected-voice actions live in the panel). The mobile slide-over is shared client UI.

### Patterns deliberately NOT applied (senior pushback)

- **Parallel routes (`@panel`)** for context panels — **rejected.** Slots are independent route segments and cannot share the page's local React state. `/history` and `/voices` panels are tightly coupled to page state; converting them would force state into the URL or a store — a behavior/architecture change with regression risk, violating "preserve UX." Documented as evaluated-and-deferred.
- **Route groups `(app)` / `(dashboard)`** — **rejected as redundant.** Exactly one chrome (the shell) is shared by *all* routes, so the **root layout** is already the correct owner. A group wrapping "all routes" adds nesting with no behavioral benefit ("do not create unnecessary complexity"). A group would become justified only if a shell-less section (auth/marketing) were introduced later.

---

## Phase 3 — Task Plan

1. Add `PageContainer` (Server).
2. Split `AppShell` → server frame + `MobileNav` + `VoicesPreloader` islands.
3. Add `app/api/layout.tsx` (Server); strip wrappers from 4 API pages.
4. Convert `/clone`, `/settings`, `/api`, `/api/voices` to Server Components.
5. Validate: `build`, `tsc --noEmit`, `eslint`, route output, client-count delta, UX parity walkthrough.

### Affected files
**New:** `shell/PageContainer.tsx`, `shell/MobileNav.tsx`, `shell/VoicesPreloader.tsx`, `app/api/layout.tsx`
**Modified:** `shell/AppShell.tsx`, `app/clone/page.tsx`, `app/settings/page.tsx`, `app/api/page.tsx`, `app/api/voices/page.tsx`, `app/api/keys/page.tsx`, `app/api/usage/page.tsx`
**Unchanged:** `PageLayout.tsx`, `PageHeader.tsx`, `app/page.tsx`, `app/history/page.tsx`, `app/voices/page.tsx`, `layout.tsx`, `Providers.tsx`
