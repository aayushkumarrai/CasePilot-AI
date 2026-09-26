# Postman Testing — Stages 1 and 2

Import these files into Postman:

- `postman/CasePilot-AI-Stage-1.postman_collection.json`
- `postman/CasePilot-AI-Stage-2.postman_collection.json`
- `postman/CasePilot-AI-Local.postman_environment.json`

Set `api_base_url` to the local or Railway URL. Keep the trailing `/v1` out of this value: the collection adds it only for versioned API routes.

## Getting a token

The collection includes Supabase **Sign up** and **Sign in** requests. Set `supabase_url` and `supabase_anon_key` in the environment, then enter a unique `test_email` and a strong `test_password` in the request body. A successful sign-in automatically stores `access_token` in the current Postman environment.

If the project requires email confirmation, confirm the account first and then run **Sign in**. The auth requests use the Supabase anonymous key only; never place a service-role key in Postman or frontend code.

## Run order

1. **Health** folder: liveness and readiness.
2. **Authentication** folder: sign up or sign in, then `GET /v1/me`.
3. **Case lifecycle** folder in order: create, list, get, update, archive, list active, list archived, restore, dashboard.
4. **Security checks** folder: remove the token to confirm `401`; sign in as a second account and run the ownership check to confirm `404`.
5. **Document intake** folder in the Stage 2 collection: request an upload URL, `PUT` raw content to that signed URL, register the object, then list and inspect the document. Run unsupported-file and retry checks as applicable.

The collection saves the created internal UUID into `case_uuid`, so no IDs need to be copied between requests.

## Expected results

| Test | Expected result |
| --- | --- |
| Health | `200`, status `ok` |
| Readiness | `200`, status `ready` |
| Sign in | `200`; an access token is stored locally by Postman |
| Me | `200`; returned `id` matches the token owner |
| Create case | `201`; saves `case_uuid` |
| Duplicate Case ID | `409` |
| Archive | `204`; normal list excludes the case |
| Restore | `200`; case becomes active again |
| Missing token | `401` |
| Other user reads first user’s case | `404` |
| Supported document upload | `201`, then progresses from `uploaded` to `ready` |
| Ready TXT/DOCX document | Detail includes stable passages |
| Ready PDF document | Detail includes a temporary `read_url` |
| Unsupported document | `201`, status `unsupported`, safe explanation |

## Security rules while testing

- Use fictional data and a dedicated test account.
- Keep access tokens in an unshared Postman environment. Do not export a populated environment or commit it.
- A bearer token identifies a user. Treat it like a temporary password.
- Use the second account only to prove isolation. Do not attempt to alter another account’s data.
- Delete test accounts from Supabase Auth after the hackathon if they are no longer needed.
