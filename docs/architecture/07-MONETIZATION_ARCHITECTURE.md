# PeakVox — Monetization Architecture

**Owns:** credits, billing, the revenue split, royalty accounting, and creator payouts.
**Cloud-only; schema-ready in CE.** Payment vendors are behind interfaces (the chosen stance);
Stripe + Stripe Connect are the first adapters.

> See also: [Data §4](03-DATA_ARCHITECTURE.md) · [Marketplace](05-MARKETPLACE_ARCHITECTURE.md)
> · [Domain §8](02-DOMAIN_ARCHITECTURE.md)

---

## 1. The money model in one picture

```
User buys credits ──► CreditLedger balance ↑   (Transaction: purchase)
        ▼
User generates speech ──► credits consumed      (Transaction: consume)
        ▼  (if a marketplace/creator voice)
gross split ──► infra share + platform margin + creator royalty
        ▼
Royalty accrued to creator (Transaction: royalty_accrual)
        ▼
periodic settlement ──► Payout via Stripe Connect (Transaction: payout)
```

**Credits** are the internal unit of account. Users buy credits (subscription and/or
top-ups); generation consumes them; creators earn a share that settles to real money via
payouts.

## 2. Vendor abstraction (interfaces first)

```
BillingProvider     purchase credits, subscriptions, invoices      → StripeBillingAdapter
PaymentProvider     charge / refund                                → StripeAdapter
PayoutProvider      onboard creators, transfer funds, settlements  → StripeConnectAdapter
```

- CE ships **Null adapters** (no-ops; billing off).
- Cloud wires the **Stripe** adapters. Swapping providers later is a new adapter, not a
  domain change — mirrors the auth seam.

## 3. Credits & the ledger

- **`CreditLedger`** holds the current balance per `owner_id` (a cached projection).
- **`transactions`** is the **append-only source of truth**: every `purchase`, `consume`,
  `royalty_accrual`, `payout`, and `adjustment` is a signed, immutable row carrying
  `balance_after` and a `ref` to the job/listing/payout. Corrections are new rows, never edits.
- Balance is reconstructable by summing transactions — the ledger row is an optimization, and
  any drift is detectable.

**Consumption pricing:** credits per generation derive from model cost class
(`models.requirements` → compute cost) and output length. The price is computed at
resolution time and **reserved before inference**, settled on success, released on failure.

## 4. Revenue split

Each royalty-bearing generation splits the gross consumption into three parts:

| Share | Goes to | Rationale |
|---|---|---|
| **Infrastructure** | platform (cost recovery) | GPU/compute/storage for the generation |
| **Platform margin** | platform | running the ecosystem |
| **Creator royalty** | the voice's creator | the voice as an economic asset |

- The split rate comes from the voice's `royalty_config` / listing `pricing`, bounded by
  platform policy (min infra recovery, max creator share).
- **Non-marketplace generations** (a user's own voice, or a built-in preset) have **no creator
  share** — gross = infra + platform only.
- Every split is recorded as a `royalties` row (`gross/creator/platform/infra` amounts) plus
  the corresponding `transactions`.

## 5. Royalty lifecycle

```
generation.completed (marketplace voice)
   ▼
accrue: compute split → Royalty(status=accrued) + Transaction(royalty_accrual, +creator)
   ▼
settle (periodic): aggregate accrued royalties per creator for the period
   ▼
Payout(status=pending) → PayoutProvider.transfer (Stripe Connect)
   ▼
Payout(status=paid) + Transaction(payout, -from creator balance)   [or failed → retry]
```

Reversals (refunds, takedowns, chargebacks) write **compensating** transactions and flip
`Royalty.status = reversed` — the ledger never mutates history.

## 6. Stripe Connect (payouts)

- **Creator onboarding:** a verified `Creator` completes Stripe Connect onboarding (Express
  recommended for the platform-managed UX); `creators.payout_account_ref` stores the connected
  account id.
- **Transfers:** settlements use Connect transfers from the platform balance to connected
  accounts; PeakVox is the merchant of record for buyers, Connect handles creator payouts +
  tax/KYC.
- **Compliance:** KYC, tax forms, and minimum-payout thresholds are handled by Connect;
  PeakVox stores only references, not bank details.

(Adapter detail; if Connect proves unfit, the `PayoutProvider` seam allows another processor.)

## 7. Billing for buyers

- **Plans:** a free tier (limited monthly credits) + paid subscription tiers + à-la-carte
  credit top-ups — all via `BillingProvider` (Stripe Billing/Checkout).
- **Metering → credits:** the Cloud metering store aggregates `generation.completed` usage;
  quota/credit checks gate generation (`402` when exhausted — see
  [API §3](04-API_ARCHITECTURE.md)).
- **Invoices/receipts:** Stripe-issued; PeakVox links them via `transactions.ref`.

## 8. CE posture

In CE: monetization tables exist (schema-ready), Null adapters are wired, all monetization
feature flags are off, and no billing/payout routers mount. Self-hosted generation is **free
and unmetered** — the infrastructure layer. Money exists only in the ecosystem layer (Cloud).
This is the open-core boundary, by design.

## 9. Integrity & auditing

- Append-only `transactions` with enforced immutability (Postgres trigger / revoked grants).
- Every financial event is traceable: `generation → royalty → transaction → payout`, linked by
  ids.
- Reconciliation jobs verify `CreditLedger.balance == Σ transactions` and
  `payouts == Σ settled royalties` per period; discrepancies alert ops.
