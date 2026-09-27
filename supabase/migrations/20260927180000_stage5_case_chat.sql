-- Stage 5: immutable, owner-scoped case chat with passage-grounded citations.

create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  exchange_id uuid not null,
  role text not null check (role in ('user', 'assistant')),
  response_type text check (response_type in ('evidence', 'general_guidance')),
  content text not null check (char_length(trim(content)) between 1 and 10000),
  created_at timestamptz not null default timezone('utc', now()),
  constraint chat_messages_role_response_check check (
    (role = 'user' and response_type is null)
    or (role = 'assistant' and response_type is not null)
  ),
  unique(exchange_id, role)
);

create table public.chat_message_citations (
  id uuid primary key default gen_random_uuid(),
  assistant_message_id uuid not null references public.chat_messages(id) on delete cascade,
  passage_id uuid not null references public.document_passages(id) on delete restrict,
  quote text not null check (char_length(trim(quote)) between 1 and 1000),
  created_at timestamptz not null default timezone('utc', now()),
  unique(assistant_message_id, passage_id, quote)
);

create index chat_messages_case_created_idx on public.chat_messages(case_id, created_at desc, id desc);
create index chat_message_citations_message_idx on public.chat_message_citations(assistant_message_id, created_at, id);
create index chat_message_citations_passage_idx on public.chat_message_citations(passage_id);

alter table public.chat_messages enable row level security;
alter table public.chat_message_citations enable row level security;

create policy "owners can view active case chat" on public.chat_messages for select to authenticated
using (exists (
  select 1 from public.cases c
  where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "owners can insert active case chat" on public.chat_messages for insert to authenticated
with check (exists (
  select 1 from public.cases c
  where c.id = case_id and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "owners can view active case chat citations" on public.chat_message_citations for select to authenticated
using (exists (
  select 1
  from public.chat_messages m
  join public.cases c on c.id = m.case_id
  where m.id = assistant_message_id and m.role = 'assistant'
    and c.owner_id = auth.uid() and c.archived_at is null
));

create policy "owners can insert active case chat citations" on public.chat_message_citations for insert to authenticated
with check (exists (
  select 1
  from public.chat_messages m
  join public.cases c on c.id = m.case_id
  where m.id = assistant_message_id and m.role = 'assistant'
    and c.owner_id = auth.uid() and c.archived_at is null
));

create function public.save_chat_exchange_with_activity(
  p_case_id uuid,
  p_question text,
  p_answer text,
  p_response_type text,
  p_citations jsonb default '[]'::jsonb
)
returns table(user_message_id uuid, assistant_message_id uuid)
language plpgsql
security invoker set search_path = public
as $$
declare
  exchange_uuid uuid := gen_random_uuid();
  user_id uuid;
  assistant_id uuid;
  citation jsonb;
  citation_passage public.document_passages;
  normalized_quote text;
  normalized_content text;
  guidance_prefix constant text := 'General guidance — not based on case documents.';
begin
  if not exists (
    select 1 from public.cases
    where id = p_case_id and owner_id = auth.uid() and archived_at is null
  ) then
    return;
  end if;

  if nullif(trim(p_question), '') is null or char_length(trim(p_question)) > 2000 then
    raise exception using errcode = '22023', message = 'Chat message must contain between 1 and 2000 characters';
  end if;
  if nullif(trim(p_answer), '') is null or char_length(trim(p_answer)) > 10000 then
    raise exception using errcode = '22023', message = 'Chat answer must contain between 1 and 10000 characters';
  end if;
  if p_response_type not in ('evidence', 'general_guidance') then
    raise exception using errcode = '22023', message = 'Invalid chat response type';
  end if;
  if jsonb_typeof(p_citations) <> 'array' or jsonb_array_length(p_citations) > 5 then
    raise exception using errcode = '22023', message = 'Chat citations must be an array of at most five items';
  end if;
  if p_response_type = 'evidence' and jsonb_array_length(p_citations) = 0 then
    raise exception using errcode = '22023', message = 'Evidence chat answers require at least one citation';
  end if;
  if p_response_type = 'general_guidance' then
    if jsonb_array_length(p_citations) <> 0 then
      raise exception using errcode = '22023', message = 'General guidance cannot include evidence citations';
    end if;
    if left(trim(p_answer), char_length(guidance_prefix)) <> guidance_prefix then
      raise exception using errcode = '22023', message = 'General guidance label is required';
    end if;
  end if;

  insert into public.chat_messages(case_id, exchange_id, role, content)
  values (p_case_id, exchange_uuid, 'user', trim(p_question))
  returning id into user_id;

  insert into public.chat_messages(case_id, exchange_id, role, response_type, content)
  values (p_case_id, exchange_uuid, 'assistant', p_response_type, trim(p_answer))
  returning id into assistant_id;

  for citation in select value from jsonb_array_elements(p_citations)
  loop
    if nullif(trim(citation ->> 'quote'), '') is null then
      raise exception using errcode = '22023', message = 'Citation quote is required';
    end if;
    select p.* into citation_passage
    from public.document_passages p
    join public.documents d on d.id = p.document_id
    where p.id = (citation ->> 'passage_id')::uuid
      and d.case_id = p_case_id and d.status = 'ready';
    if not found then
      raise exception using errcode = '22023', message = 'Citation passage does not belong to this ready case evidence';
    end if;
    normalized_quote := lower(regexp_replace(trim(citation ->> 'quote'), '\s+', ' ', 'g'));
    normalized_content := lower(regexp_replace(trim(citation_passage.content), '\s+', ' ', 'g'));
    if position(normalized_quote in normalized_content) = 0 then
      raise exception using errcode = '22023', message = 'Citation quote was not found in the cited passage';
    end if;
    insert into public.chat_message_citations(assistant_message_id, passage_id, quote)
    values (assistant_id, citation_passage.id, trim(citation ->> 'quote'));
  end loop;

  insert into public.activity_events(case_id, actor_id, action, details)
  values (
    p_case_id,
    auth.uid(),
    'chat_exchange_completed',
    jsonb_build_object(
      'user_message_id', user_id,
      'assistant_message_id', assistant_id,
      'response_type', p_response_type
    )
  );

  return query select user_id, assistant_id;
end;
$$;

grant execute on function public.save_chat_exchange_with_activity(uuid, text, text, text, jsonb) to authenticated;
