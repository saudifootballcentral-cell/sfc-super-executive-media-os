# Pipeline — Build

Stage: `build` · Owner: build-engineer

## Preconditions
qa_playtest and optimization gates passed; console zero-warning; scene list and product
name/version set.

## Produce
Unity batch mode (`-batchmode -nographics -quit -executeMethod`), Linux and/or WebGL per
spec. On the shared VM, no other heavy stage may run during a build.

## Verify
Artifact launches and reaches the main menu. Log to memory:
`memory.py log versions '{"event":"build","game":...,"platform":...,"artifact":...,"result":...}'`.
A failing build bisects against the last green `versions` entry.

## Gate
Verified artifact + versions entry.
