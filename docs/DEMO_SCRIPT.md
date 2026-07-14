# Persona — 3-minute demo script (narration + on-screen cues)

**How to use:** read the **bold** lines aloud; do the `[ON SCREEN]` action as you speak. App is at
**http://127.0.0.1:8137**. Two minds: **`neuro`** (spawned live for this demo, actively working) and
**`curie-3c33`** (running for days — the deep results). Backup stills: `results/demo_media/`. ~3:00 total.

---

## 0:00 — Intro (0:00–0:15)
`[ON SCREEN]` Persona home / gallery, or the `neuro` Focus tab.
> **"Hi — I'm Aryan Singh, biomedical engineering and computer science at Johns Hopkins. This is
> Persona: a synthetic researcher that doesn't just answer questions — it keeps reading, keeps
> believing, and keeps working while you're gone."**

## 0:15 — The problem (0:15–0:35)
`[ON SCREEN]` stay on Focus; gesture at the stream of activity.
> **"Biomedical literature is too big to read and too easy to fake fluency over. Tools today retrieve
> papers and summarize them — but a summary hides what a scientist actually needs: which claims are
> exact, which are independent, which are contested, which are testable, and which are worth your time.
> Confident prose makes unsupported claims look like knowledge."**

## 0:35 — What Persona is, and how it goes further (0:35–0:55)
`[ON SCREEN]` Focus — point to the "self" rail: interests, open questions.
> **"Persona isn't a chat session. It's a persistent mind. It has its own interests, its own memory, a
> notebook of what it's thinking, and a budget it spends carefully. It reads at scale, but it's
> disciplined about what it's allowed to believe — and it produces real outputs: reviews, reanalyses,
> and dossiers that tell a human what to do next."**

## 0:55 — Ignition (0:55–1:15)
`[ON SCREEN]` switch to `neuro` → **Floor** tab. Show the Director + parallel team lanes.
> **"Here it is igniting. I gave it three interests in neurodegeneration; it woke up, turned them into
> its own open questions, and spawned teams of bounded agents — right now, dozens in flight across four
> teams reading in parallel. A membrane sits in front of memory and decides what's even allowed to
> become a belief. And it's doing this live, on a real twenty-five-dollar budget."**

## 1:15 — The Focus board (1:15–1:35)
`[ON SCREEN]` **Focus** tab (on `neuro` or `curie-3c33` for a fuller stream).
> **"This is the Focus board — its living notebook. Every move is legible: noticed a claim, spawned
> readers, found support or a contradiction, updated a belief, flagged something for a human. For a
> researcher, this is the audit trail — you can see exactly why it believes what it believes, not just
> the final answer."**

## 1:35 — The knowledge graph (1:35–2:00)
`[ON SCREEN]` `openMind('curie-3c33')` → **Map ▸ Graph**.
> **"Switch to a mind that's read for days. Everything it knows is a knowledge graph — over five
> thousand claims and five thousand entities — and every node is provenance-typed: read, inferred,
> tested, or human-confirmed, each colored differently. So a researcher can instantly separate what's
> proven from what's merely mentioned once. Model confidence never gets the visual authority of a
> confirmed fact."**

## 2:00 — Tensions + the human handoff (2:00–2:25)
`[ON SCREEN]` **Map ▸ Field map** (⚡ tensions) → **Review** → open one evidence dossier.
> **"The Field map shows the structure of the field — forty subtopics and sixty-two open tensions.
> When two exact quotes collide, Persona doesn't pick a winner. It opens an evidence dossier and routes
> it to a human — here, sixty-two candidate conflicts waiting for review, each with both quotes and the
> discriminating check. In one case it caught a contradiction that was its own extraction error, and
> corrected itself on the record. That's the discipline: scale of reading, discipline of believing."**

## 2:25 — The acting loop + deliverables (2:25–2:50)
`[ON SCREEN]` **Work ▸ Research** → open **Matched-donor GEO self-test** session (CONTESTED). Then
scroll its conclusions; optionally **Studio** for the generated papers.
> **"Then it acts. A literature tension became a prespecified, falsifiable question, a real public GEO
> dataset, and a reanalysis that reran twenty out of twenty times to the exact hash — for zero dollars.
> The predicted effect wasn't there: an honest falsification. And notice — the computation is 'verified'
> while the interpretation is 'contested.' Two separate verdicts. It even writes the next experiment for
> a human, and drafts full cited reviews as deliverables."**

## 2:50 — Close (2:50–3:00)
`[ON SCREEN]` **Map ▸ Field rests on** (value queue) or hold on the deliverables.
> **"scite, Open Targets, PaperQA2 — they retrieve, classify, summarize. None of them act, and none
> keep a persistent, believing self. That's Persona: a mind that remembers what it believes and why,
> tests what it can, and hands you what it can't resolve alone. Thanks for watching."**

---

## Tab visit order (with the console shortcut)
1. `neuro` **Focus** — `setSurface('stream')` (intro/problem/self)
2. `neuro` **Floor** — `setSurface('swarm')` (ignition, teams)
3. `curie-3c33` **Map ▸ Graph** — `openMind('curie-3c33')` then `setSurface('graph')`
4. **Map ▸ Field map** — `setSurface('fieldmap')` (tensions)
5. **Review** — `setSurface('instruments')` → click "open evidence dossier"
6. **Work ▸ Research** — `setSurface('studios')` → open the Matched-donor GEO session
7. **Studio** — `setSurface('studio')` (deliverables) · **Map ▸ Field rests on** — `setSurface('field')`

## Real numbers (all on screen — say them exactly)
- Live `neuro` Floor: ~**4 teams**, dozens of agents in flight, spending against a **$25** cap.
- `curie-3c33` graph: **5,418 claims · 5,081 entities · 124 contradiction edges**.
- Field map: **40 subtopics · 62 open tensions**. Review: **62 candidate conflicts** awaiting review.
- GEO session: **CONTESTED**, deterministic/no-model, **58 events · 30 hash-checked artifacts · $0.0000**;
  GSE1297 β **0.1071** [0.0245, 0.2817], LOO **7/7**; GSE28146 crosses zero → inconclusive.
  "Trace integrity verifies lineage, **not** scientific truth."

## Continuous read-through (if you'd rather not stop)
Hi, I'm Aryan Singh — biomedical engineering and computer science at Johns Hopkins. This is Persona, a
synthetic researcher that doesn't just answer questions; it keeps reading, believing, and working while
you're gone. Biomedical literature is too big to read and too easy to fake fluency over. Today's tools
retrieve and summarize — but a summary hides what a scientist needs: which claims are exact, independent,
contested, testable, and worth your time. Persona isn't a chat session — it's a persistent mind, with its
own interests, memory, a notebook of its thinking, and a budget. Here it's igniting: I gave it three
neurodegeneration interests, it turned them into its own questions and spawned four teams of agents
reading in parallel, right now, on a real $25 budget — with a membrane deciding what's even allowed to
become a belief. This Focus board is its living notebook: every move is legible, so you see why it
believes something, not just the answer. Here's a mind that's read for days — a knowledge graph of over
five thousand claims, every node typed by provenance, so proven and merely-mentioned never look alike.
The Field map shows sixty-two open tensions; when exact quotes collide, Persona opens an evidence dossier
and routes it to a human — it even caught a contradiction that was its own extraction error and corrected
itself on the record. Then it acts: a tension became a prespecified question, a public GEO dataset, and a
reanalysis that reran twenty out of twenty times to the exact hash for zero dollars — an honest
falsification, with the computation verified but the interpretation contested. It writes the next
experiment for a human and drafts cited reviews. scite, Open Targets, PaperQA2 retrieve and summarize —
none of them act, and none keep a persistent believing self. That's Persona: a mind that remembers what
it believes and why, tests what it can, and hands you what it can't resolve alone. Thanks for watching.
