create or replace function public.fail_analysis_run_with_activity(p_analysis_run_id uuid, p_error_message text)
returns setof public.analysis_runs
language plpgsql
security invoker set search_path = public
as $$
declare
  failed_run public.analysis_runs;
begin
  update public.analysis_runs r
  set status = 'failed',
      error_message = left(coalesce(nullif(trim(p_error_message), ''), 'Analysis could not be completed.'), 500),
      completed_at = timezone('utc', now())
  from public.cases c
  where r.id = p_analysis_run_id and c.id = r.case_id and c.owner_id = auth.uid()
    and c.archived_at is null and r.status in ('queued', 'processing')
  returning r.* into failed_run;
  if not found then return; end if;

  update public.cases
  set status = case when exists (
    select 1 from public.analysis_runs
    where case_id = failed_run.case_id and status = 'completed'
  ) then 'review'::public.case_status else 'draft'::public.case_status end
  where id = failed_run.case_id and owner_id = auth.uid() and archived_at is null;

  insert into public.activity_events(case_id, actor_id, action, details)
  values (failed_run.case_id, auth.uid(), 'analysis_failed', jsonb_build_object('analysis_run_id', failed_run.id));
  return next failed_run;
end;
$$;
