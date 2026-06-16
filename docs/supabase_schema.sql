create table if not exists public.crashlab_runs (
  run_id text primary key,
  target_id text,
  target_name text,
  target_kind text,
  target_profile jsonb not null default '{}'::jsonb,
  target_spec jsonb not null default '{}'::jsonb,
  status text,
  run_mode text,
  created_at bigint,
  completed_at bigint,
  score integer,
  outcome text,
  summary text,
  run_meta jsonb not null default '{}'::jsonb,
  category_scores jsonb not null default '{}'::jsonb,
  logs jsonb not null default '[]'::jsonb
);

create index if not exists crashlab_runs_created_at_idx on public.crashlab_runs(created_at desc);
create index if not exists crashlab_runs_target_id_idx on public.crashlab_runs(target_id);

create table if not exists public.crashlab_cases (
  id bigint generated always as identity primary key,
  run_id text not null,
  case_id text,
  category text,
  prompt text,
  variant boolean not null default false,
  passed boolean,
  result_status text,
  case_score integer,
  response_text text,
  notes text,
  meta jsonb not null default '{}'::jsonb
);

create index if not exists crashlab_cases_run_id_idx on public.crashlab_cases(run_id);

create table if not exists public.crashlab_configured_targets (
  id text primary key,
  payload jsonb not null,
  created_at bigint not null,
  updated_at bigint not null
);

create index if not exists crashlab_configured_targets_updated_at_idx on public.crashlab_configured_targets(updated_at desc);

create table if not exists public.crashlab_test_plans (
  plan_id text primary key,
  target_id text not null,
  mode text not null,
  source text not null,
  approved boolean not null default true,
  created_at bigint not null,
  updated_at bigint not null,
  payload jsonb not null
);

create index if not exists crashlab_test_plans_target_mode_idx on public.crashlab_test_plans(target_id, mode, updated_at desc);

create table if not exists public.crashlab_target_probes (
  target_id text primary key,
  payload jsonb not null,
  created_at bigint not null,
  updated_at bigint not null
);
