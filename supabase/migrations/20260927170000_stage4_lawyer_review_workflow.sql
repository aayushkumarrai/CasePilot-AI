-- Stage 4: lawyer decisions remain distinct from immutable AI suggestions and citations.

alter table public.case_fields
  add column reviewed_value text,
  add column reviewed_at timestamptz,
  add column reviewed_by uuid references public.profiles(id) on delete set null;

alter table public.case_parties
  add column reviewed_name text,
  add column reviewed_role text,
  add column reviewed_at timestamptz,
  add column reviewed_by uuid references public.profiles(id) on delete set null;

alter table public.case_fields
  add constraint case_fields_reviewed_value_check
  check (reviewed_value is null or char_length(trim(reviewed_value)) between 1 and 4000);

alter table public.case_parties
  add constraint case_parties_reviewed_name_check
  check (reviewed_name is null or char_length(trim(reviewed_name)) between 1 and 200),
  add constraint case_parties_reviewed_role_check
  check (reviewed_role is null or char_length(trim(reviewed_role)) between 1 and 100);

create index case_fields_review_status_idx on public.case_fields(status, reviewed_at desc);
create index case_parties_review_status_idx on public.case_parties(status, reviewed_at desc);

create table public.manual_tasks (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  title text not null check (char_length(trim(title)) between 1 and 200),
  description text not null check (char_length(trim(description)) between 1 and 4000),
  status public.task_status not null default 'proposed',
  created_by uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index manual_tasks_case_status_idx on public.manual_tasks(case_id, status, updated_at desc);
create trigger manual_tasks_set_updated_at before update on public.manual_tasks
for each row execute function public.set_updated_at();

alter table public.manual_tasks enable row level security;
create policy "owners can view manual tasks" on public.manual_tasks for select to authenticated
using (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid()));
create policy "owners can create manual tasks" on public.manual_tasks for insert to authenticated
with check (
  created_by = auth.uid()
  and exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null)
);
create policy "owners can update manual tasks" on public.manual_tasks for update to authenticated
using (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null))
with check (exists (select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null));

create function public.review_case_field_with_activity(
  p_case_id uuid,
  p_field_id uuid,
  p_action text,
  p_reviewed_value text default null
)
returns setof public.case_fields
language plpgsql
security invoker set search_path = public
as $$
declare
  target public.case_fields;
  action_name text;
begin
  select cf.* into target
  from public.case_fields cf
  join public.analysis_runs r on r.id = cf.analysis_run_id
  join public.cases c on c.id = r.case_id
  where cf.id = p_field_id and r.case_id = p_case_id and c.owner_id = auth.uid() and c.archived_at is null;
  if not found then return; end if;
  if p_action not in ('confirm', 'edit', 'reject') then
    raise exception using errcode = '22023', message = 'Unsupported field review action';
  end if;
  if target.status = 'rejected' then
    raise exception using errcode = '22023', message = 'Rejected fields cannot be changed';
  end if;
  if p_action = 'confirm' then
    if target.status <> 'pending' then raise exception using errcode = '22023', message = 'Only pending fields can be confirmed'; end if;
    update public.case_fields set status = 'confirmed', reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'field_confirmed';
  elsif p_action = 'edit' then
    if nullif(trim(p_reviewed_value), '') is null then raise exception using errcode = '22023', message = 'A replacement value is required'; end if;
    update public.case_fields set status = 'confirmed', reviewed_value = trim(p_reviewed_value), reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'field_edited';
  else
    update public.case_fields set status = 'rejected', reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'field_rejected';
  end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (p_case_id, auth.uid(), action_name, jsonb_build_object('field_id', target.id));
  return next target;
end;
$$;

create function public.review_case_party_with_activity(
  p_case_id uuid,
  p_party_id uuid,
  p_action text,
  p_reviewed_name text default null,
  p_reviewed_role text default null
)
returns setof public.case_parties
language plpgsql
security invoker set search_path = public
as $$
declare
  target public.case_parties;
  action_name text;
begin
  select cp.* into target
  from public.case_parties cp
  join public.analysis_runs r on r.id = cp.analysis_run_id
  join public.cases c on c.id = r.case_id
  where cp.id = p_party_id and r.case_id = p_case_id and c.owner_id = auth.uid() and c.archived_at is null;
  if not found then return; end if;
  if p_action not in ('confirm', 'edit', 'reject') then
    raise exception using errcode = '22023', message = 'Unsupported party review action';
  end if;
  if target.status = 'rejected' then
    raise exception using errcode = '22023', message = 'Rejected parties cannot be changed';
  end if;
  if p_action = 'confirm' then
    if target.status <> 'pending' then raise exception using errcode = '22023', message = 'Only pending parties can be confirmed'; end if;
    update public.case_parties set status = 'confirmed', reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'party_confirmed';
  elsif p_action = 'edit' then
    if nullif(trim(p_reviewed_name), '') is null and nullif(trim(p_reviewed_role), '') is null then
      raise exception using errcode = '22023', message = 'A replacement name or role is required';
    end if;
    update public.case_parties
    set status = 'confirmed',
        reviewed_name = coalesce(nullif(trim(p_reviewed_name), ''), target.reviewed_name),
        reviewed_role = coalesce(nullif(trim(p_reviewed_role), ''), target.reviewed_role),
        reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'party_edited';
  else
    update public.case_parties set status = 'rejected', reviewed_at = timezone('utc', now()), reviewed_by = auth.uid()
    where id = target.id returning * into target;
    action_name := 'party_rejected';
  end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (p_case_id, auth.uid(), action_name, jsonb_build_object('party_id', target.id));
  return next target;
end;
$$;

create function public.create_manual_task_with_activity(p_case_id uuid, p_title text, p_description text)
returns setof public.manual_tasks
language plpgsql
security invoker set search_path = public
as $$
declare
  target public.manual_tasks;
begin
  if not exists (select 1 from public.cases where id = p_case_id and owner_id = auth.uid() and archived_at is null) then return; end if;
  if nullif(trim(p_title), '') is null or nullif(trim(p_description), '') is null then
    raise exception using errcode = '22023', message = 'Manual task title and description are required';
  end if;
  insert into public.manual_tasks(case_id, title, description, created_by)
  values (p_case_id, trim(p_title), trim(p_description), auth.uid()) returning * into target;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (p_case_id, auth.uid(), 'manual_task_created', jsonb_build_object('task_id', target.id));
  return next target;
end;
$$;

create function public.update_manual_task_with_activity(
  p_task_id uuid,
  p_title text default null,
  p_description text default null,
  p_new_status text default null
)
returns setof public.manual_tasks
language plpgsql
security invoker set search_path = public
as $$
declare
  target public.manual_tasks;
  action_name text;
begin
  select mt.* into target from public.manual_tasks mt join public.cases c on c.id = mt.case_id
  where mt.id = p_task_id and c.owner_id = auth.uid() and c.archived_at is null;
  if not found then return; end if;
  if p_new_status is not null and (p_title is not null or p_description is not null) then
    raise exception using errcode = '22023', message = 'Edit task text or change status in separate requests';
  end if;
  if p_new_status is not null then
    if (target.status = 'proposed' and p_new_status = 'approved') then action_name := 'task_approved';
    elsif (target.status = 'proposed' and p_new_status = 'rejected') then action_name := 'task_rejected';
    elsif (target.status = 'approved' and p_new_status = 'done') then action_name := 'task_completed';
    else raise exception using errcode = '22023', message = 'Invalid task status transition'; end if;
    update public.manual_tasks set status = p_new_status::public.task_status where id = target.id returning * into target;
  else
    if target.status not in ('proposed', 'approved') then raise exception using errcode = '22023', message = 'Only open manual tasks can be edited'; end if;
    if p_title is null and p_description is null then raise exception using errcode = '22023', message = 'Provide a task edit or status change'; end if;
    if p_title is not null and nullif(trim(p_title), '') is null then raise exception using errcode = '22023', message = 'Task title cannot be empty'; end if;
    if p_description is not null and nullif(trim(p_description), '') is null then raise exception using errcode = '22023', message = 'Task description cannot be empty'; end if;
    update public.manual_tasks set title = coalesce(trim(p_title), target.title), description = coalesce(trim(p_description), target.description)
    where id = target.id returning * into target;
    action_name := 'manual_task_updated';
  end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (target.case_id, auth.uid(), action_name, jsonb_build_object('task_id', target.id));
  return next target;
end;
$$;

create function public.transition_ai_task_with_activity(p_task_id uuid, p_new_status text)
returns setof public.tasks
language plpgsql
security invoker set search_path = public
as $$
declare
  target public.tasks;
  target_case_id uuid;
  action_name text;
begin
  select t.* into target
  from public.tasks t join public.analysis_runs r on r.id = t.analysis_run_id join public.cases c on c.id = r.case_id
  where t.id = p_task_id and c.owner_id = auth.uid() and c.archived_at is null;
  if not found then return; end if;
  select case_id into target_case_id from public.analysis_runs where id = target.analysis_run_id;
  if target.status = 'proposed' and p_new_status = 'approved' then action_name := 'task_approved';
  elsif target.status = 'proposed' and p_new_status = 'rejected' then action_name := 'task_rejected';
  elsif target.status = 'approved' and p_new_status = 'done' then action_name := 'task_completed';
  else raise exception using errcode = '22023', message = 'Invalid task status transition'; end if;
  update public.tasks set status = p_new_status::public.task_status where id = target.id returning * into target;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (target_case_id, auth.uid(), action_name, jsonb_build_object('task_id', target.id));
  return next target;
end;
$$;

grant execute on function public.review_case_field_with_activity(uuid, uuid, text, text) to authenticated;
grant execute on function public.review_case_party_with_activity(uuid, uuid, text, text, text) to authenticated;
grant execute on function public.create_manual_task_with_activity(uuid, text, text) to authenticated;
grant execute on function public.update_manual_task_with_activity(uuid, text, text, text) to authenticated;
grant execute on function public.transition_ai_task_with_activity(uuid, text) to authenticated;
