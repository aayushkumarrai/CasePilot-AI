create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create type public.case_status as enum ('draft', 'processing', 'review', 'ready');

create table public.cases (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  external_case_id text not null check (char_length(trim(external_case_id)) between 1 and 80),
  case_name text not null check (char_length(trim(case_name)) between 1 and 160),
  status public.case_status not null default 'draft',
  archived_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create unique index cases_owner_active_external_case_id_key
  on public.cases(owner_id, external_case_id)
  where archived_at is null;

create table public.activity_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  actor_id uuid not null references public.profiles(id) on delete cascade,
  actor_type text not null default 'user' check (actor_type in ('user', 'ai', 'system')),
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index activity_events_case_created_at_idx on public.activity_events(case_id, created_at desc);

create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger cases_set_updated_at
before update on public.cases
for each row execute function public.set_updated_at();

create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (
    new.id,
    coalesce(new.email, ''),
    nullif(new.raw_user_meta_data ->> 'display_name', '')
  );
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.cases enable row level security;
alter table public.activity_events enable row level security;

create policy "users can view their own profile"
on public.profiles for select
to authenticated
using (id = auth.uid());

create policy "users can update their own profile"
on public.profiles for update
to authenticated
using (id = auth.uid())
with check (id = auth.uid());

create policy "users can view their own cases"
on public.cases for select
to authenticated
using (owner_id = auth.uid());

create policy "users can create their own cases"
on public.cases for insert
to authenticated
with check (owner_id = auth.uid());

create policy "users can update their own cases"
on public.cases for update
to authenticated
using (owner_id = auth.uid())
with check (owner_id = auth.uid());

create policy "users can view activity for their cases"
on public.activity_events for select
to authenticated
using (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid()));

create policy "users can add activity for their cases"
on public.activity_events for insert
to authenticated
with check (
  actor_id = auth.uid()
  and exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid())
);

create function public.create_case_with_activity(p_external_case_id text, p_case_name text)
returns setof public.cases
language plpgsql
security invoker set search_path = public
as $$
declare
  created_case public.cases;
begin
  insert into public.cases(owner_id, external_case_id, case_name)
  values (auth.uid(), trim(p_external_case_id), trim(p_case_name))
  returning * into created_case;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (created_case.id, auth.uid(), 'case_created', jsonb_build_object('case_id', created_case.external_case_id));
  return next created_case;
end;
$$;

create function public.update_case_with_activity(
  p_case_id uuid,
  p_external_case_id text,
  p_case_name text,
  p_changed_fields text[]
)
returns setof public.cases
language plpgsql
security invoker set search_path = public
as $$
declare
  updated_case public.cases;
begin
  update public.cases
  set external_case_id = trim(p_external_case_id), case_name = trim(p_case_name)
  where id = p_case_id and archived_at is null
  returning * into updated_case;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (updated_case.id, auth.uid(), 'case_updated', jsonb_build_object('changed_fields', p_changed_fields));
  return next updated_case;
end;
$$;

create function public.archive_case_with_activity(p_case_id uuid)
returns setof public.cases
language plpgsql
security invoker set search_path = public
as $$
declare
  archived_case public.cases;
begin
  update public.cases
  set archived_at = timezone('utc', now())
  where id = p_case_id and archived_at is null
  returning * into archived_case;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action)
  values (archived_case.id, auth.uid(), 'case_archived');
  return next archived_case;
end;
$$;

create function public.restore_case_with_activity(p_case_id uuid)
returns setof public.cases
language plpgsql
security invoker set search_path = public
as $$
declare
  restored_case public.cases;
begin
  update public.cases
  set archived_at = null
  where id = p_case_id and archived_at is not null
  returning * into restored_case;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action)
  values (restored_case.id, auth.uid(), 'case_restored');
  return next restored_case;
end;
$$;

grant execute on function public.create_case_with_activity(text, text) to authenticated;
grant execute on function public.update_case_with_activity(uuid, text, text, text[]) to authenticated;
grant execute on function public.archive_case_with_activity(uuid) to authenticated;
grant execute on function public.restore_case_with_activity(uuid) to authenticated;
