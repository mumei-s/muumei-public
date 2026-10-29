# MUUMEI public distribution

Public URL: https://mumei-s.github.io/muumei-public/
Participant-only sample: https://mumei-s.github.io/muumei-public/review/

This repository holds compiled files only. The canonical source is the private
`mumei-s/muumei` repository. Public information, actual member/Auth pages and the
isolated participant sample are built from source
`7cb5ac9ba27467b9b7bc0045bcab96bc2e963333`.

The public introduction has no member data or backend connection. The participant
sample uses fictional device-local content and empty backend configuration.
Actual member/Auth pages keep their existing auth storage and runtime public
configuration endpoint. New registration remains closed (`ready=false`).

`/jobs` and `/direct` are static work guides with no script, form or submission.
Actual-member work routes redirect to these guides before creating a form.

The interface has pearl/rose and dark-plum themes, distinct round profile icons,
visible member cards and short feature explanations. Post comment and board
reply interfaces are removed; the separate production database policy migration
is pending explicit rollout approval. Likes, standalone posts and OWNER chat
remain available within their existing authorization gates.

No OWNER distribution, source code, SQL, environment files, privileged keys or
source maps are included. Auth, email, separate OWNER hosting and device Push
setup/E2E remain separate release gates. No paid plan or service is added.
