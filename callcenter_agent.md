# Call Center Integration Guide

This guide explains the minimal APIs your call-center or AI agent needs to interact with the dialer panel.

## Auth for the dialer
- Use the shared `DIALER_TOKEN` from backend `.env` as a Bearer token.
- All dialer endpoints live under `/api/dialer/*`.

## Get next batch to dial
- **GET** `/api/dialer/next-batch?size={optional}`
- Headers: `Authorization: Bearer <DIALER_TOKEN>`
- Response when dialing is allowed:
  ```json
  {
    "call_allowed": true,
    "timezone": "Asia/Tehran",
    "server_time": "ISO8601",
    "schedule_version": 3,
    "active_agents": [
      { "id": 5, "full_name": "Ali Ahmadi", "phone_number": "0912..." }
    ],
    "batch": {
      "batch_id": "uuid",
      "size_requested": 100,
      "size_returned": 73,
      "numbers": [ { "id": 1, "phone_number": "09123456789" } ]
    }
  }
  ```
- Response when not allowed:
  ```json
  {
    "call_allowed": false,
    "timezone": "Asia/Tehran",
    "server_time": "ISO8601",
    "schedule_version": 3,
    "reason": "disabled | holiday | no_window | outside_allowed_time_window",
    "retry_after_seconds": 600
  }
  ```
- Notes: obey `call_allowed`; back off for `retry_after_seconds`. `size` is optional; capped by server config.

## Report call result
- **POST** `/api/dialer/report-result`
- Headers: `Authorization: Bearer <DIALER_TOKEN>`
- Payload:
  ```json
  {
    "number_id": 1,                // optional if phone_number provided
    "phone_number": "0912...",    // required
    "status": "CONNECTED | FAILED | NOT_INTERESTED | MISSED | HANGUP | DISCONNECTED | BUSY | POWER_OFF | BANNED | UNKNOWN",
    "reason": "optional text",
    "attempted_at": "ISO8601 timestamp",
    "call_allowed": true | false,   // optional: toggles global enable flag
    "agent_id": 5,                 // optional
    "agent_phone": "0912...",     // optional; used if id missing
    "user_message": "customer message/comment"
  }
  ```
- Behavior:
  - Updates number status and clears its batch assignment.
  - Logs a `call_attempt` with `status`, `reason`, `user_message`, and agent info (if provided).
  - Assigns the number to the provided agent (by `agent_id` or `agent_phone`) and stores `user_message` as the latest note for that number.
  - If `call_allowed` is provided, it flips the global dialer enable flag accordingly.

## Status rules to honor
- Mutable via UI/admin bulk: `IN_QUEUE`, `MISSED`, `BUSY`, `POWER_OFF`, `BANNED`.
- Immutable (cannot be changed/deleted by admins/agents): `CONNECTED`, `FAILED`, `NOT_INTERESTED`, `HANGUP`, `DISCONNECTED`, `UNKNOWN`.
- Dialer can still report any status above; the restriction is for panel users.

## Admin/agent roster (if needed by call center)
- **GET** `/api/admins` (Bearer JWT from admin login) returns all users/agents with `id`, `username`, `role`, `first_name`, `last_name`, `phone_number`, `is_active`.
- `active_agents` are also included in `next-batch` to help the call center map calls to agents.

## Numbers export (for supervision/debug)
- **POST** `/api/numbers/export` (admin JWT)
- Body mirrors bulk selection: `ids` OR `select_all` with filters (`status`, `search`, `start_date`, `end_date`, `agent_id`, `excluded_ids`, `sort_by`, `sort_order`). Returns XLSX with phone, status, attempts, timestamps, assigned agent, last user message.

## Timezone
- All server-side times are Asia/Tehran. Send/expect ISO 8601 timestamps with timezone when reporting results.

Keep the dialer token secret. If the server responds with `call_allowed=false`, pause fetching until `retry_after_seconds` elapses.
