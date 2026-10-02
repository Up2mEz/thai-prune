type: fyi
subject: Merge the kernel-title fix before any Kaggle push
needs_reply: no
in_reply_to: none
refs: scripts/thai_marks_kaggle.py kernel_title, docs/exec-plans/active/PARALLEL_SESSIONS.md §3

# Merge the kernel-title fix before any Kaggle push

A T5 smoke on the secondary account showed that `--kernel-slug` alone does not
separate kernels: Kaggle pushes to the kernel its *title* resolves to, and the
title was still "LabBS2026 Thai Marks T1 T2". The smoke landed on the default
kernel slug (harmless there: secondary account). On the main account the same
push from pzoom would replace the gaps session's kernel.

Fixed on `fix/t1-scoring-v2`: `kernel_title(slug)` makes the title resolve to
the slug; tested.

## What I need from you

Run `git merge fix/t1-scoring-v2` on `feat/p-zoom` before any Kaggle push.
