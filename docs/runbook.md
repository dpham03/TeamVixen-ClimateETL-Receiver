# Runbook

> **What goes here:** step-by-step instructions that someone who wasn't on your team can
> follow without asking you: exact commands and what each one should print. Test it by
> having a teammate follow it from a fresh terminal. Delete these notes before you tag
> `handoff`.

## Connect

*How to connect from VS Code and from Python, and how to check that it worked.*

## Refresh the data

*For each source: the exact command, how often to run it, how long it usually takes, and
what it prints when it succeeds.*

## Check the output

*How to tell the refresh worked: row counts, the newest date loaded, the tests in
`sql/tests/`, your schema's size against the 2 GB budget, and what normal looks like for
each.*

## When something fails

| What you see | What it means | What to do |
|---|---|---|
| *(example)* `refresh.py` stops with "Validation failed; nothing was loaded: negative precipitation: 12" | The source sent bad values; nothing was loaded | Look at the bad rows, decide whether to drop or fix them, record the decision under Known issues in `docs/technical-spec.md`, and rerun |

## Recover

*How to get back to a good state after a failed or bad load: what to rerun, in what
order, and how to confirm it worked.*

## Who owns what

*After the handoff, which team is responsible for each part, and who to ask about the
original design.*
