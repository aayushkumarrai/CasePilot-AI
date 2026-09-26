create type public.document_status as enum ('uploaded', 'processing', 'ready', 'failed', 'unsupported');

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  file_name text not null check (char_length(trim(file_name)) between 1 and 255),
  content_type text not null,
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 52428800),
  storage_path text,
  status public.document_status not null default 'uploaded',
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint documents_storage_path_status_check check (
    (status = 'unsupported' and storage_path is null)
    or (status <> 'unsupported' and storage_path is not null)
  )
);

create index documents_case_created_at_idx on public.documents(case_id, created_at desc);

create table public.document_passages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents(id) on delete cascade,
  sequence_number integer not null check (sequence_number > 0),
  page_number integer check (page_number > 0),
  passage_label text not null,
  content text not null check (char_length(content) > 0),
  created_at timestamptz not null default timezone('utc', now()),
  unique(document_id, sequence_number)
);

create index document_passages_document_sequence_idx on public.document_passages(document_id, sequence_number);

create trigger documents_set_updated_at
before update on public.documents
for each row execute function public.set_updated_at();

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'case-documents',
  'case-documents',
  false,
  52428800,
  array['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

alter table public.documents enable row level security;
alter table public.document_passages enable row level security;

create policy "users can view documents for their cases"
on public.documents for select to authenticated
using (exists (
  select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid()
));

create policy "users can insert documents for their cases"
on public.documents for insert to authenticated
with check (exists (
  select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "users can update documents for their cases"
on public.documents for update to authenticated
using (exists (
  select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid()
))
with check (exists (
  select 1 from public.cases c where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "users can view passages for their documents"
on public.document_passages for select to authenticated
using (exists (
  select 1
  from public.documents d
  join public.cases c on c.id = d.case_id
  where d.id = document_id and c.owner_id = auth.uid()
));

create policy "users can insert passages for their documents"
on public.document_passages for insert to authenticated
with check (exists (
  select 1
  from public.documents d
  join public.cases c on c.id = d.case_id
  where d.id = document_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "users can delete passages for their documents"
on public.document_passages for delete to authenticated
using (exists (
  select 1
  from public.documents d
  join public.cases c on c.id = d.case_id
  where d.id = document_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "users can upload files to their own storage prefix"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'case-documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "users can read files from their own storage prefix"
on storage.objects for select to authenticated
using (
  bucket_id = 'case-documents'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create function public.register_document_with_activity(
  p_case_id uuid,
  p_file_name text,
  p_content_type text,
  p_size_bytes bigint,
  p_storage_path text,
  p_status public.document_status,
  p_error_message text default null
)
returns setof public.documents
language plpgsql
security invoker set search_path = public
as $$
declare
  created_document public.documents;
  active_document_count integer;
  event_action text;
begin
  if not exists (
    select 1 from public.cases
    where id = p_case_id and owner_id = auth.uid() and archived_at is null
  ) then
    return;
  end if;

  select count(*) into active_document_count from public.documents where case_id = p_case_id;
  if active_document_count >= 50 then
    raise exception using errcode = '23505', message = 'A case can contain at most 50 documents';
  end if;

  insert into public.documents(case_id, file_name, content_type, size_bytes, storage_path, status, error_message)
  values (p_case_id, trim(p_file_name), p_content_type, p_size_bytes, p_storage_path, p_status, p_error_message)
  returning * into created_document;

  event_action := case when p_status = 'unsupported' then 'document_unsupported' else 'document_uploaded' end;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (
    p_case_id,
    auth.uid(),
    event_action,
    jsonb_build_object('document_id', created_document.id, 'file_name', created_document.file_name)
  );
  return next created_document;
end;
$$;

create function public.start_document_processing_with_activity(p_document_id uuid, p_action text)
returns setof public.documents
language plpgsql
security invoker set search_path = public
as $$
declare
  updated_document public.documents;
begin
  update public.documents d
  set status = 'processing', error_message = null
  from public.cases c
  where d.id = p_document_id and c.id = d.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and d.status in ('uploaded', 'failed')
  returning d.* into updated_document;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (updated_document.case_id, auth.uid(), p_action, jsonb_build_object('document_id', updated_document.id));
  return next updated_document;
end;
$$;

create function public.complete_document_processing_with_activity(p_document_id uuid, p_passages jsonb)
returns setof public.documents
language plpgsql
security invoker set search_path = public
as $$
declare
  updated_document public.documents;
begin
  update public.documents d
  set status = 'ready', error_message = null
  from public.cases c
  where d.id = p_document_id and c.id = d.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and d.status = 'processing'
  returning d.* into updated_document;
  if not found then return; end if;

  delete from public.document_passages where document_id = p_document_id;
  insert into public.document_passages(document_id, sequence_number, page_number, passage_label, content)
  select p_document_id, x.sequence_number, x.page_number, x.passage_label, x.content
  from jsonb_to_recordset(p_passages) as x(sequence_number integer, page_number integer, passage_label text, content text);

  insert into public.activity_events(case_id, actor_id, action, details)
  values (updated_document.case_id, auth.uid(), 'document_ready', jsonb_build_object('document_id', updated_document.id));
  return next updated_document;
end;
$$;

create function public.fail_document_processing_with_activity(p_document_id uuid, p_error_message text)
returns setof public.documents
language plpgsql
security invoker set search_path = public
as $$
declare
  updated_document public.documents;
begin
  update public.documents d
  set status = 'failed', error_message = left(p_error_message, 500)
  from public.cases c
  where d.id = p_document_id and c.id = d.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and d.status = 'processing'
  returning d.* into updated_document;
  if not found then return; end if;
  insert into public.activity_events(case_id, actor_id, action, details)
  values (updated_document.case_id, auth.uid(), 'document_failed', jsonb_build_object('document_id', updated_document.id));
  return next updated_document;
end;
$$;

grant execute on function public.register_document_with_activity(uuid, text, text, bigint, text, public.document_status, text) to authenticated;
grant execute on function public.start_document_processing_with_activity(uuid, text) to authenticated;
grant execute on function public.complete_document_processing_with_activity(uuid, jsonb) to authenticated;
grant execute on function public.fail_document_processing_with_activity(uuid, text) to authenticated;
