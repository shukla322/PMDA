# Credential concern: evidence and scope

The existing PRD section on security records an earlier plaintext-credential concern in the external VECTOR+ repository. The implementation status identifies an external `chat.py` file and states it was not copied or executed. This turn has verified those historical notes, not the original token's existence, validity, provider, ownership or revocation status.

The project owner does not know which key was referenced. Do not record revocation as complete, request that a secret be pasted into chat, or treat a fresh paid API key as a requirement for Stages 1–5. Current BTP work uses local tools and public data without an LLM key.

Status: historical external concern, unverified. Keep it separate from BTP's source-scanning and secret-management controls. If the external integration is ever needed, inspect it with secret-redacted tooling, identify the provider without exposing the token, and resolve any confirmed issue before reuse. Do not copy potentially credential-bearing source into BTP.
