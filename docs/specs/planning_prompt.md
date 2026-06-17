Read docs/drafts/concept_test_planning.md in full. It captures the design for extending the interview engine to support concept-test methodology. The v1 scope, ontology, strategy set, and phase sequence are locked.
Write an implementation spec for Phase 0 + Phase 1 only. 
Before writing, surface any ambiguities in the planning doc that would force you to guess.

Add a short "agent routing" section at the top listing which existing agent covers which part, so the implementation session picks up the right specialist without having to derive it.

When creating beads
- One epic: concept-test-v1 — covers Phases 0 through 5.
- One bead for the spec itself: "Write Phase 0+1 implementation spec" — type: task, priority: 2, recommended_model: opus. 

Acceptance: spec exists at docs/specs/concept_test_phase_0_1.md, passes spec-loopability-auditor, open questions from the planning doc are resolved.

- Implementation beads created after the spec lands. Don't create them now. Beading unwritten work commits you to interpretations you'll revise.
- Dependency: all newly created implementation beads depend on the spec bead closing.

What I would NOT do:
- Don't create beads for later phases yet. Their scope will shift after thisphase lands.
- Don't create a bead per phase without decomposition. "Implement Phase" is too big to be loopable.
- Don't use TaskCreate for any of this. It's multi-session by construction.