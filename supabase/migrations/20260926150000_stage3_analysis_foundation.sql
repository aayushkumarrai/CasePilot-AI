create type public.analysis_run_status as enum ('queued', 'processing', 'completed', 'failed');
create type public.review_status as enum ('pending', 'confirmed', 'rejected');
create type public.timeline_date_confidence as enum ('exact', 'month', 'year', 'unknown');
create type public.finding_kind as enum ('conflict', 'gap');
create type public.task_status as enum ('proposed', 'approved', 'done', 'rejected');
create type public.citation_target_type as enum (
  'document_summary', 'case_field', 'case_party', 'timeline_event', 'finding', 'task'
);

alter table public.cases
  add column lawyer_context text,
  add constraint cases_lawyer_context_length_check
    check (lawyer_context is null or char_length(lawyer_context) <= 4000);

create table public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  status public.analysis_run_status not null default 'queued',
  lawyer_context_snapshot text,
  case_summary text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint analysis_runs_context_length_check
    check (lawyer_context_snapshot is null or char_length(lawyer_context_snapshot) <= 4000),
  constraint analysis_runs_error_length_check
    check (error_message is null or char_length(error_message) <= 500),
  constraint analysis_runs_completion_check
    check ((status in ('queued', 'processing') and completed_at is null) or status in ('completed', 'failed'))
);

create unique index analysis_runs_one_active_per_case_key
  on public.analysis_runs(case_id)
  where status in ('queued', 'processing');
create index analysis_runs_case_completed_at_idx
  on public.analysis_runs(case_id, completed_at desc)
  where status = 'completed';

create table public.document_summaries (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  document_id uuid not null references public.documents(id) on delete restrict,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  summary text not null check (char_length(trim(summary)) > 0),
  created_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, document_id),
  unique(analysis_run_id, source_ref)
);

create table public.case_fields (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  field_key text not null check (char_length(trim(field_key)) between 1 and 100),
  label text not null check (char_length(trim(label)) between 1 and 160),
  value text not null check (char_length(trim(value)) > 0),
  status public.review_status not null default 'pending',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, source_ref)
);

create table public.case_parties (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  name text not null check (char_length(trim(name)) between 1 and 200),
  role text not null check (char_length(trim(role)) between 1 and 100),
  status public.review_status not null default 'pending',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, source_ref)
);

create table public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  event_date_text text not null check (char_length(trim(event_date_text)) between 1 and 100),
  date_confidence public.timeline_date_confidence not null default 'unknown',
  title text not null check (char_length(trim(title)) between 1 and 200),
  description text not null check (char_length(trim(description)) > 0),
  created_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, source_ref)
);

create table public.findings (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  kind public.finding_kind not null,
  title text not null check (char_length(trim(title)) between 1 and 200),
  description text not null check (char_length(trim(description)) > 0),
  created_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, source_ref)
);

create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  finding_id uuid references public.findings(id) on delete set null,
  source_ref text not null check (char_length(trim(source_ref)) between 1 and 100),
  title text not null check (char_length(trim(title)) between 1 and 200),
  description text not null check (char_length(trim(description)) > 0),
  status public.task_status not null default 'proposed',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique(analysis_run_id, source_ref)
);

create table public.analysis_citations (
  id uuid primary key default gen_random_uuid(),
  passage_id uuid not null references public.document_passages(id) on delete restrict,
  target_type public.citation_target_type not null,
  document_summary_id uuid references public.document_summaries(id) on delete cascade,
  case_field_id uuid references public.case_fields(id) on delete cascade,
  case_party_id uuid references public.case_parties(id) on delete cascade,
  timeline_event_id uuid references public.timeline_events(id) on delete cascade,
  finding_id uuid references public.findings(id) on delete cascade,
  task_id uuid references public.tasks(id) on delete cascade,
  quote text not null check (char_length(trim(quote)) between 1 and 1000),
  created_at timestamptz not null default timezone('utc', now()),
  constraint analysis_citations_exactly_one_target_check check (
    num_nonnulls(document_summary_id, case_field_id, case_party_id, timeline_event_id, finding_id, task_id) = 1
  ),
  constraint analysis_citations_target_type_check check (
    (target_type = 'document_summary' and document_summary_id is not null)
    or (target_type = 'case_field' and case_field_id is not null)
    or (target_type = 'case_party' and case_party_id is not null)
    or (target_type = 'timeline_event' and timeline_event_id is not null)
    or (target_type = 'finding' and finding_id is not null)
    or (target_type = 'task' and task_id is not null)
  )
);

create index document_summaries_run_idx on public.document_summaries(analysis_run_id);
create index case_fields_run_idx on public.case_fields(analysis_run_id, status);
create index case_parties_run_idx on public.case_parties(analysis_run_id, status);
create index timeline_events_run_idx on public.timeline_events(analysis_run_id, created_at);
create index findings_run_idx on public.findings(analysis_run_id, kind);
create index tasks_run_idx on public.tasks(analysis_run_id, status);
create index analysis_citations_passage_idx on public.analysis_citations(passage_id);
create index analysis_citations_document_summary_idx on public.analysis_citations(document_summary_id) where document_summary_id is not null;
create index analysis_citations_case_field_idx on public.analysis_citations(case_field_id) where case_field_id is not null;
create index analysis_citations_case_party_idx on public.analysis_citations(case_party_id) where case_party_id is not null;
create index analysis_citations_timeline_event_idx on public.analysis_citations(timeline_event_id) where timeline_event_id is not null;
create index analysis_citations_finding_idx on public.analysis_citations(finding_id) where finding_id is not null;
create index analysis_citations_task_idx on public.analysis_citations(task_id) where task_id is not null;

create trigger analysis_runs_set_updated_at before update on public.analysis_runs
for each row execute function public.set_updated_at();
create trigger case_fields_set_updated_at before update on public.case_fields
for each row execute function public.set_updated_at();
create trigger case_parties_set_updated_at before update on public.case_parties
for each row execute function public.set_updated_at();
create trigger tasks_set_updated_at before update on public.tasks
for each row execute function public.set_updated_at();

alter table public.analysis_runs enable row level security;
alter table public.document_summaries enable row level security;
alter table public.case_fields enable row level security;
alter table public.case_parties enable row level security;
alter table public.timeline_events enable row level security;
alter table public.findings enable row level security;
alter table public.tasks enable row level security;
alter table public.analysis_citations enable row level security;

create policy "owners can view analysis runs" on public.analysis_runs for select to authenticated
using (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid()));
create policy "owners can write analysis runs" on public.analysis_runs for all to authenticated
using (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view document summaries" on public.document_summaries for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write document summaries" on public.document_summaries for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view case fields" on public.case_fields for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write case fields" on public.case_fields for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view case parties" on public.case_parties for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write case parties" on public.case_parties for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view timeline events" on public.timeline_events for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write timeline events" on public.timeline_events for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view findings" on public.findings for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write findings" on public.findings for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view tasks" on public.tasks for select to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid()));
create policy "owners can write tasks" on public.tasks for all to authenticated
using (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id where r.id = analysis_run_id and c.owner_id = auth.uid() and c.archived_at is null));

create policy "owners can view analysis citations" on public.analysis_citations for select to authenticated
using (exists (
  select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id
  left join public.document_summaries ds on ds.id = document_summary_id
  left join public.case_fields cf on cf.id = case_field_id
  left join public.case_parties cp on cp.id = case_party_id
  left join public.timeline_events te on te.id = timeline_event_id
  left join public.findings f on f.id = finding_id
  left join public.tasks t on t.id = task_id
  where c.owner_id = auth.uid() and r.id = coalesce(ds.analysis_run_id, cf.analysis_run_id, cp.analysis_run_id, te.analysis_run_id, f.analysis_run_id, t.analysis_run_id)
));
create policy "owners can write analysis citations" on public.analysis_citations for all to authenticated
using (exists (
  select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id
  left join public.document_summaries ds on ds.id = document_summary_id
  left join public.case_fields cf on cf.id = case_field_id
  left join public.case_parties cp on cp.id = case_party_id
  left join public.timeline_events te on te.id = timeline_event_id
  left join public.findings f on f.id = finding_id
  left join public.tasks t on t.id = task_id
  where c.owner_id = auth.uid() and c.archived_at is null
    and r.id = coalesce(ds.analysis_run_id, cf.analysis_run_id, cp.analysis_run_id, te.analysis_run_id, f.analysis_run_id, t.analysis_run_id)
))
with check (exists (
  select 1 from public.analysis_runs r join public.cases c on c.id = r.case_id
  left join public.document_summaries ds on ds.id = document_summary_id
  left join public.case_fields cf on cf.id = case_field_id
  left join public.case_parties cp on cp.id = case_party_id
  left join public.timeline_events te on te.id = timeline_event_id
  left join public.findings f on f.id = finding_id
  left join public.tasks t on t.id = task_id
  where c.owner_id = auth.uid() and c.archived_at is null
    and r.id = coalesce(ds.analysis_run_id, cf.analysis_run_id, cp.analysis_run_id, te.analysis_run_id, f.analysis_run_id, t.analysis_run_id)
));

create function public.start_analysis_run_with_activity(p_case_id uuid, p_lawyer_context text default null)
returns setof public.analysis_runs
language plpgsql
security invoker set search_path = public
as $$
declare
  created_run public.analysis_runs;
  normalized_context text := nullif(trim(p_lawyer_context), '');
begin
  if normalized_context is not null and char_length(normalized_context) > 4000 then
    raise exception using errcode = '22001', message = 'Lawyer-provided context must be at most 4000 characters';
  end if;
  if not exists (select 1 from public.cases where id = p_case_id and owner_id = auth.uid() and archived_at is null) then
    return;
  end if;
  if not exists (select 1 from public.documents where case_id = p_case_id and status = 'ready') then
    raise exception using errcode = '22023', message = 'At least one ready document is required for analysis';
  end if;
  update public.cases set lawyer_context = normalized_context, status = 'processing'
  where id = p_case_id and owner_id = auth.uid() and archived_at is null;
  insert into public.analysis_runs(case_id, status, lawyer_context_snapshot)
  values (p_case_id, 'queued', normalized_context)
  returning * into created_run;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (p_case_id, auth.uid(), 'analysis_started', jsonb_build_object('analysis_run_id', created_run.id));
  return next created_run;
end;
$$;

create function public.mark_analysis_run_processing_with_activity(p_analysis_run_id uuid)
returns setof public.analysis_runs
language plpgsql
security invoker set search_path = public
as $$
declare
  updated_run public.analysis_runs;
begin
  update public.analysis_runs r set status = 'processing', started_at = timezone('utc', now())
  from public.cases c
  where r.id = p_analysis_run_id and c.id = r.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and r.status = 'queued'
  returning r.* into updated_run;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (updated_run.case_id, auth.uid(), 'analysis_processing', jsonb_build_object('analysis_run_id', updated_run.id));
  return next updated_run;
end;
$$;

create function public.complete_analysis_run_with_outputs(
  p_analysis_run_id uuid,
  p_case_summary text,
  p_document_summaries jsonb default '[]'::jsonb,
  p_case_fields jsonb default '[]'::jsonb,
  p_case_parties jsonb default '[]'::jsonb,
  p_timeline_events jsonb default '[]'::jsonb,
  p_findings jsonb default '[]'::jsonb,
  p_tasks jsonb default '[]'::jsonb,
  p_citations jsonb default '[]'::jsonb
)
returns setof public.analysis_runs
language plpgsql
security invoker set search_path = public
as $$
declare
  completed_run public.analysis_runs;
  item jsonb;
  citation jsonb;
  target_id uuid;
  target_run_id uuid;
  finding_target_id uuid;
begin
  update public.analysis_runs r set status = 'completed', case_summary = nullif(trim(p_case_summary), ''), error_message = null, completed_at = timezone('utc', now())
  from public.cases c
  where r.id = p_analysis_run_id and c.id = r.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and r.status = 'processing'
  returning r.* into completed_run;
  if not found then return; end if;

  for item in select value from jsonb_array_elements(p_document_summaries)
  loop
    if not exists (select 1 from public.documents where id = (item ->> 'document_id')::uuid and case_id = completed_run.case_id) then
      raise exception using errcode = '23503', message = 'Document summary references a document outside this case';
    end if;
    insert into public.document_summaries(analysis_run_id, document_id, source_ref, summary)
    values (completed_run.id, (item ->> 'document_id')::uuid, item ->> 'ref', item ->> 'summary');
  end loop;
  for item in select value from jsonb_array_elements(p_case_fields)
  loop
    insert into public.case_fields(analysis_run_id, source_ref, field_key, label, value)
    values (completed_run.id, item ->> 'ref', item ->> 'field_key', item ->> 'label', item ->> 'value');
  end loop;
  for item in select value from jsonb_array_elements(p_case_parties)
  loop
    insert into public.case_parties(analysis_run_id, source_ref, name, role)
    values (completed_run.id, item ->> 'ref', item ->> 'name', item ->> 'role');
  end loop;
  for item in select value from jsonb_array_elements(p_timeline_events)
  loop
    insert into public.timeline_events(analysis_run_id, source_ref, event_date_text, date_confidence, title, description)
    values (completed_run.id, item ->> 'ref', item ->> 'event_date_text', coalesce((item ->> 'date_confidence')::public.timeline_date_confidence, 'unknown'), item ->> 'title', item ->> 'description');
  end loop;
  for item in select value from jsonb_array_elements(p_findings)
  loop
    insert into public.findings(analysis_run_id, source_ref, kind, title, description)
    values (completed_run.id, item ->> 'ref', (item ->> 'kind')::public.finding_kind, item ->> 'title', item ->> 'description');
  end loop;
  for item in select value from jsonb_array_elements(p_tasks)
  loop
    finding_target_id := null;
    if nullif(item ->> 'finding_ref', '') is not null then
      select id into finding_target_id from public.findings where analysis_run_id = completed_run.id and source_ref = item ->> 'finding_ref';
      if finding_target_id is null then
        raise exception using errcode = '23503', message = 'Task references a finding outside this run';
      end if;
    end if;
    insert into public.tasks(analysis_run_id, finding_id, source_ref, title, description)
    values (completed_run.id, finding_target_id, item ->> 'ref', item ->> 'title', item ->> 'description');
  end loop;
  for citation in select value from jsonb_array_elements(p_citations)
  loop
    target_id := null;
    case citation ->> 'target_type'
      when 'document_summary' then select id into target_id from public.document_summaries where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      when 'case_field' then select id into target_id from public.case_fields where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      when 'case_party' then select id into target_id from public.case_parties where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      when 'timeline_event' then select id into target_id from public.timeline_events where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      when 'finding' then select id into target_id from public.findings where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      when 'task' then select id into target_id from public.tasks where analysis_run_id = completed_run.id and source_ref = citation ->> 'target_ref';
      else raise exception using errcode = '22023', message = 'Citation has an invalid target type';
    end case;
    if target_id is null then
      raise exception using errcode = '23503', message = 'Citation target does not belong to this run';
    end if;
    select d.case_id into target_run_id from public.document_passages dp join public.documents d on d.id = dp.document_id where dp.id = (citation ->> 'passage_id')::uuid;
    if target_run_id is distinct from completed_run.case_id then
      raise exception using errcode = '23503', message = 'Citation passage does not belong to this case';
    end if;
    insert into public.analysis_citations(passage_id, target_type, document_summary_id, case_field_id, case_party_id, timeline_event_id, finding_id, task_id, quote)
    values (
      (citation ->> 'passage_id')::uuid,
      (citation ->> 'target_type')::public.citation_target_type,
      case when citation ->> 'target_type' = 'document_summary' then target_id end,
      case when citation ->> 'target_type' = 'case_field' then target_id end,
      case when citation ->> 'target_type' = 'case_party' then target_id end,
      case when citation ->> 'target_type' = 'timeline_event' then target_id end,
      case when citation ->> 'target_type' = 'finding' then target_id end,
      case when citation ->> 'target_type' = 'task' then target_id end,
      citation ->> 'quote'
    );
  end loop;
  update public.cases set status = 'review' where id = completed_run.case_id and owner_id = auth.uid() and archived_at is null;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (completed_run.case_id, auth.uid(), 'analysis_completed', jsonb_build_object('analysis_run_id', completed_run.id));
  return next completed_run;
end;
$$;

create function public.fail_analysis_run_with_activity(p_analysis_run_id uuid, p_error_message text)
returns setof public.analysis_runs
language plpgsql
security invoker set search_path = public
as $$
declare
  failed_run public.analysis_runs;
begin
  update public.analysis_runs r set status = 'failed', error_message = left(coalesce(nullif(trim(p_error_message), ''), 'Analysis could not be completed.'), 500), completed_at = timezone('utc', now())
  from public.cases c
  where r.id = p_analysis_run_id and c.id = r.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and r.status in ('queued', 'processing')
  returning r.* into failed_run;
  if not found then return; end if;
  update public.cases set status = case when exists (
    select 1 from public.analysis_runs where case_id = failed_run.case_id and status = 'completed'
  ) then 'review' else 'draft' end
  where id = failed_run.case_id and owner_id = auth.uid() and archived_at is null;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (failed_run.case_id, auth.uid(), 'analysis_failed', jsonb_build_object('analysis_run_id', failed_run.id));
  return next failed_run;
end;
$$;

grant execute on function public.start_analysis_run_with_activity(uuid, text) to authenticated;
grant execute on function public.mark_analysis_run_processing_with_activity(uuid) to authenticated;
grant execute on function public.complete_analysis_run_with_outputs(uuid, text, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb, jsonb) to authenticated;
grant execute on function public.fail_analysis_run_with_activity(uuid, text) to authenticated;
