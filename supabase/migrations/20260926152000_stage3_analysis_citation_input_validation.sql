create or replace function public.complete_analysis_run_with_outputs(
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
  target_case_id uuid;
  finding_target_id uuid;
  citation_passage_id uuid;
begin
  update public.analysis_runs r set status = 'completed', case_summary = nullif(trim(p_case_summary), ''), error_message = null, completed_at = timezone('utc', now())
  from public.cases c
  where r.id = p_analysis_run_id and c.id = r.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and r.status = 'processing'
  returning r.* into completed_run;
  if not found then return; end if;

  for item in select value from jsonb_array_elements(p_document_summaries)
  loop
    if nullif(item ->> 'document_id', '') is null or not exists (select 1 from public.documents where id = (item ->> 'document_id')::uuid and case_id = completed_run.case_id) then
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
    if nullif(citation ->> 'passage_id', '') is null then
      raise exception using errcode = '22023', message = 'Citation passage_id is required';
    end if;
    begin
      citation_passage_id := (citation ->> 'passage_id')::uuid;
    exception when invalid_text_representation then
      raise exception using errcode = '22023', message = 'Citation passage_id must be a UUID';
    end;
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
    select d.case_id into target_case_id from public.document_passages dp join public.documents d on d.id = dp.document_id where dp.id = citation_passage_id;
    if target_case_id is distinct from completed_run.case_id then
      raise exception using errcode = '23503', message = 'Citation passage does not belong to this case';
    end if;
    insert into public.analysis_citations(passage_id, target_type, document_summary_id, case_field_id, case_party_id, timeline_event_id, finding_id, task_id, quote)
    values (
      citation_passage_id,
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
