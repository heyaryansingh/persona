# AGENTS.md — Persona

> **Persona** is a persistent, always-on synthetic researcher for the biomedical literature. It maintains a durable **self** (interests, beliefs, memory, taste) and uses an ephemeral **swarm** of bounded agents to read at scale, closing an agentic loop from a flagged contradiction → falsifiable hypothesis → located public dataset → first-pass reanalysis → written back into its belief-state, escalating to humans exactly when it needs wet-lab results or experimental judgment.
>
> Read `BUILD_PLAN.md` in full before doing anything. It is the source of truth for architecture, the intellectual engine, and the sequenced build. This file governs *how you work* while building it.

---

## 0. The prime directive: work like a scientist, not a code monkey

You are not here to pattern-match the nearest plausible implementation. You are here to **investigate, hypothesize, test, and only then build** — the same posture Persona itself embodies. Every non-trivial decision follows the loop in §2. If you find yourself about to write code because it "seems right," stop: that feeling is a hypothesis, not evidence.

The one-line test for whether you're doing it right: **could you defend this choice to a skeptical PhD reviewer with a number, a citation, or a run result?** If not, you haven't finished thinking.

---

## 1. Never assume. Anything.

This is the hardest and most important rule, so it is first among the specifics.

- **Never assume a library's behavior** — check its version and test the actual call in a scratch script before relying on it. APIs drift; your training data is stale.
- **Never assume a technique is state-of-the-art because you remember it that way.** Search. The field moves monthly. What you "know" about continual learning, agent memory, retrieval, or extraction may be a year out of date. Verify against current work before designing around it.
- **Never assume your data looks how you expect.** Inspect it. Print shapes, ranges, nulls, distributions. Look at ten real rows before writing the eleventh line of processing.
- **Never assume a result is real because it's the result you wanted.** A number that confirms your hypothesis deserves *more* scrutiny, not less. Re-run with new seeds. Check for the confound (see the `exp_memory_core → exp_memory_v2 → exp_when_protection_matters` progression in `/experiments` — v1 gave a flattering-but-wrong answer, and the whole point was catching *why*).
- **Never assume an architectural choice from `BUILD_PLAN.md` is settled if it isn't marked `[E]`** (evidence-backed). Unmarked choices are hypotheses awaiting a test.
- **Never assume the user's framing is complete.** If a requirement is ambiguous or a decision hinges on unstated context, surface it — don't paper over it with a guess.
- **When you don't know, say so, then go find out.** "I'm not sure how X behaves; let me test it" beats a confident wrong answer every time.

If you catch yourself using the words "should" or "probably" about anything checkable — that's your cue to check it.

---

## 2. The research-and-verify workflow (mandatory for non-trivial decisions)

Before implementing any architectural, modeling, or algorithmic choice that isn't already marked `[E]` in the build plan:

1. **State it as a hypothesis with a metric.** "Approach A beats B on metric M under condition C." Vague hypotheses produce vague experiments.
2. **Search the current literature first.** Has someone solved or studied this in the last ~18 months? Stand on it or beat it — don't reinvent it blind. Cite what you find.
3. **Write a minimal sandboxed experiment** under `/experiments`. Real code: Python, plus ML / RL / stats / small models as the question demands. Isolate the one thing you're testing.
4. **Run it ≥ 20 seeds.** Report mean ± 95% CI. A single run is an anecdote. Save the script to `/experiments` and results to `/results`.
5. **If the evidence contradicts your assumption, follow the evidence** and write down the reversal explicitly. Reversals are the most valuable thing you produce — they're where the real knowledge is.
6. **Only then implement**, and cite the experiment in a code comment (`# see experiments/exp_X.py — chose A over B, +0.17 acc under correlated noise`).
7. **Keep everything reproducible** (seed everything) and **verify results more than once** before you build on them.

This is not bureaucracy. It is the difference between a system that works and one that merely runs. The build plan was written this way; the experiments in `/results/FINDINGS.md` are proof the method finds truths you'd otherwise miss.

**Do not gold-plate the process, either.** Trivial, reversible choices (a variable name, a plotting color) don't need an experiment. Reserve the full loop for decisions that are load-bearing, expensive to reverse, or genuinely uncertain. Judgment about *which* is which is itself part of working like a scientist.

---

## 3. Use the actual cutting edge to make actual advances

Persona is meant to do things that were not possible before. Aim there.

- **Prefer a genuinely novel, evidence-backed mechanism over a safe, known one** — *when* the novel one earns its place in a test. Novelty for its own sake is slop; novelty that measurably wins is the whole point.
- **Actively pull in recent advances**: current agent-memory systems, surprise/priority replay, retrieval architectures, calibration methods, multi-agent orchestration, structured extraction. Search for them, evaluate them, adapt them — don't hand-roll a worse version of something the field already refined.
- **The bar for "advance" is empirical**, not rhetorical: a real advance shows up as a better number on a metric that matters, or a capability nothing else has. If you can't measure the improvement, you haven't made one yet.
- When you invent something, **try to falsify it before you celebrate it.** The strongest ideas survive your own attempts to break them.

---

## 4. Code principles

- **Correctness first, then clarity, then performance.** Never optimize what you haven't measured; never trust what you haven't tested.
- **Small, pure, testable units.** Every module in the architecture (see `BUILD_PLAN.md` §5.1, §10.1) should have a clean interface and its own tests. Side effects isolated; the swarm agents in particular must be pure and independently testable.
- **Test at the seams that matter.** The membrane's poisoning-resistance is validated by reusing `experiments/exp_when_protection_matters.py` as a test oracle (build plan §10.1) — real behavior, not mocked assertions. Write tests that would actually catch a regression in the thing you care about.
- **Fail loud, fail early.** Validate inputs at boundaries. A silent wrong number that propagates into the belief-state is the worst possible bug in this system.
- **Provenance and reproducibility are features, not chores.** Every belief is provenance-typed (`READ / INFERRED / HUMAN_CONFIRMED / TESTED`); every experiment is seeded; every result is saved. Never confuse "the model thinks X" with "X is true."
- **Cache aggressively for the demo** (Europe PMC, Open Targets, dataset lookups, and any pre-run Codex Science result) so nothing live can break the money-shot.
- **Comment the *why*, not the *what*.** Especially: cite the experiment or paper behind any non-obvious choice.
- **Reuse the ecosystem, build the contribution.** Stand on Europe PMC / Open Targets / SemMedDB / ClinicalTrials.gov / GEO. Build fresh only what's genuinely new: the self, the membrane+anchoring, the loops, the intellectual engine, the legibility layer.
- **Leave the repo runnable at every checkpoint.** The day-by-day plan (§9.6) is sequenced so there's always a working demo — preserve that property.

---

## 5. Design principles (the product is legibility)

Persona must read as *a mind at work*, not a dashboard. A user should be able to look over its shoulder and see what it's thinking, what it cares about right now, and why.

- **Legibility over polish.** The living notebook — a timestamped stream of the researcher's real moves ("noticed → suspected → spawned N readers → found 3 support / 1 contra → updated belief → flagged for human") — is the beating heart. Make its reasoning visible and auditable everywhere.
- **Show the funnel, not just the output.** The swarm reading at scale and the membrane admitting/rejecting candidates *is* the story ("scale of reading, discipline of believing"). Don't hide the machinery that earns trust.
- **Honest uncertainty in the UI.** Surface calibrated confidence and provenance state. Never present an inferred belief with the visual authority of a confirmed one.
- **Motion only for real state change** — a belief updating, an agent returning, a contradiction firing. No decorative animation.
- **Aesthetic direction** (see `BUILD_PLAN.md` §6): calm, editorial, notebook-like — a scientist's bound journal crossed with a live systems console. Monospace for the researcher's voice; serif for synthesized reviews; restrained palette with one accent for *live activity*, one for *needs-human*.
- **Every screen answers a question a real researcher asks**: what does the field actually rest on (dependency graph), where is the argument heading (trajectory), what's the highest-leverage experiment (value queue), what needs my judgment (handoff inbox). If a screen doesn't answer a real question, cut it.
- Consult the `frontend-design` skill before building UI, and justify the stack rather than defaulting to it.

---

## 6. Plan carefully, then execute (be creative in *what*, disciplined in *how*)

- **Think before you build.** For anything non-trivial, write the plan down first: the hypothesis, the approach, the alternatives you considered, the acceptance criteria. Planning is cheap; rebuilding is not.
- **Be genuinely creative in ideas, implementations, and designs.** Explore more than one approach. The best solution is often not the first one that compiles. Brainstorm, prototype, compare — the intellectual engine (§3 of the build plan) exists because someone pushed past the obvious "literature search tool" framing.
- **But hold creativity accountable to evidence.** A creative idea earns its place by winning a test or unlocking a capability, not by sounding impressive. Steelman your own ideas *and* try to kill them.
- **Prefer the reversible, demoable increment.** Ship the smallest thing that proves the concept, verify it, then extend. The day-by-day sequence is built this way on purpose.
- **When uncertain between paths, run the small experiment that discriminates them** rather than debating in prose. Let evidence break ties.
- **Record decisions and their rationale** as you go (extend `/results/FINDINGS.md` and the self's `strategies.md`) so the reasoning compounds and, at the end, compiles into the paper: *"On constructing a persistent, continuously-learning synthetic researcher."*

---

## 7. Standing reminders

- Persona cannot do wet-lab work. The **human-as-resolver** division of labor is a design feature, not a limitation — route real experimental judgment to humans and anchor their answers (validated: anchoring retained 100% of verified beliefs under correlated poisoning vs 71% naive — see `/results/FINDINGS.md`).
- Keep the **self small** and the **swarm disposable**. Scale lives in the swarm; identity lives in the self.
- Name the competitors honestly (scite, Open Targets, PaperQA2, MedKGent, KARMA, AutoBioKG) and build the piece they don't have: the *acting* loop and the persistent self.
- Every time you're about to guess — search, test, or ask instead.
