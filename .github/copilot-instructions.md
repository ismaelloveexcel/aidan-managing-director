# Copilot Instructions — Arie Finance

## About this project
Arie Finance is a Mauritius-based financial services startup. I (Ismael) am the AI & Automation Lead.
These repos are internal tools, client portals, and automation workflows for the business.

## My role & goals
- Build sales automation, CRM workflows, client onboarding tools, and management reporting
- Minimize manual intervention at every step — if something can be automated, automate it
- Build for a small team: lean, pragmatic, production-ready code only

## Tech stack
- **Frontend**: Next.js App Router (TypeScript), Tailwind CSS
- **Backend**: Supabase (PostgreSQL + RLS + Edge Functions)
- **Auth**: Supabase Auth
- **Payments**: Lemon Squeezy
- **Deployment**: Vercel
- **Package manager**: pnpm
- **Monorepo**: Turborepo (when applicable)

## Coding standards
- TypeScript strict mode always
- No `any` types — use proper types or `unknown`
- Prefer server components and server actions in Next.js
- Always use Row Level Security (RLS) on Supabase tables
- Keep components small and composable
- Error handling must be explicit — never swallow errors silently
- Environment variables go in `.env.local` (never hardcode secrets)
- Use Zod for all input validation

## Supabase patterns
- Always generate TypeScript types from schema: `supabase gen types typescript`
- Use `supabase/migrations` for all schema changes — never alter DB manually
- Enable RLS on every table, write policies before inserting data

## What I want from Copilot
- Suggest automation opportunities when you see repetitive patterns
- Flag when something could be a Supabase Edge Function instead of client-side code
- Always suggest the most scalable, low-touch solution
- If I ask for a form, also suggest the server action and validation
- Remind me to add RLS policies when creating new tables

