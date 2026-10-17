# Routine Watch — Product Spec & Handoff

Hackathon: **Hack the Valley 11** (36 h). Team owner: Ian Leung (Discord `thelegend12`).
Status: idea locked, nothing built yet. This doc is the spec, not an implementation plan.
Architecture diagram: `routine-watch-diagram.png` (same folder).

---

## 1. One-liner

A privacy-preserving camera system that watches residents of a care home do everyday tasks (making tea, getting dressed) and alerts nurses when their **task errors suddenly spike against their own normal**, an early sign of **delirium**, which is often caused by a UTI, dehydration or a new medication. Every alert shows the evidence.

## 2. Problem

- Delirium is sudden confusion. It is common, dangerous, and often missed in long-term care, especially the "quiet" kind (hypoactive delirium).
- It is often the first visible sign of an infection, dehydration or a drug reaction. Catching it a day or two earlier can prevent an ER trip.
- Staff are stretched thin and can't watch every resident do every task. Formal screens like the CAM (Confusion Assessment Method) are done occasionally, not continuously.
- Mistakes in everyday tasks are a well-documented, measurable sign of confusion. The categories are skipping a step, doing steps out of order, repeating a step, using the wrong object, and hesitating.

## 3. Users

- **Primary:** the charge nurse or care aide on shift, who receives the alerts and acts on them.
- **Secondary:** the wellness director or physician, who reviews trends.
- **Subject:** the resident, who is never shown a dashboard and is never identifiable in stored data.

## 4. Hackathon targets (drive scope decisions)

| Prize | Fit | What it requires from us |
|---|---|---|
| PointClickCare "Catch It Early" | Primary | Care-team UI, real AI, a realistic health scenario. Bonus for explaining *why* something was flagged. |
| Best Healthcare Innovation | Strong | The same project. |
| Top 3 overall | Stretch | A polished live demo. |
| MLH Best Use of Gemini API | Easy | Gemini used as the vision verifier. |
| MLH Best Use of Tiger Data | Easy | Event and error time-series stored in Tiger Data (TimescaleDB). |
| MLH Best Use of Vultr | Easy | Backend hosted on Vultr. |
| MLH GoDaddy domain | Trivial | Register a domain for the demo URL. |
| DEV writing challenge | Post-event | A build write-up. |

PointClickCare judging criteria: **Usefulness, Clarity, Creativity, Execution, Use of AI**. The sponsor explicitly allows synthetic data.

## 5. Scope

### MVP (must have for demo)
1. **One task end to end: making tea.** Live camera → step events → task graph → error detection.
2. **Privacy filter:** only skeleton and object-box data leave the capture device. Raw frames are never stored.
3. **Per-resident baseline** from synthetic history (about 14 days) plus the live session.
4. **Change detection** that produces a "possible delirium" flag.
5. **Explained alert:** the exact errors with timestamps, a short clip or skeleton replay, a plain-language summary, and suggested checks.
6. **Nurse dashboard** with a resident list, the alert, the live task map and the evidence view.
7. **Nurse feedback:** a one-tap "confirmed" or "false alarm" on each alert.

### Nice to have (in priority order)
1. **Ghost replay:** today's skeleton laid over the resident's normal routine.
2. **Heat calendar** of errors per resident per day.
3. **Push alert** to a phone.
4. **A second task**, such as getting dressed or taking medication with water, to show it generalises.
5. **Care-record context** (new meds, fever, fluid intake) shown next to the alert.
6. **"Slow drift" trend view**, separate from the sudden-change flag.

### Non-goals
- Diagnosing delirium or any condition. It flags a change for a human to review; it never diagnoses.
- Fall detection. That's a crowded market (Teton, SafelyYou and others), so stay out of it.
- Guiding or prompting the resident through the task. That's existing prior art (COACH, CHEF-VL, RegulAR); our product is aimed at staff.
- Real patient data, or any integration with an electronic health record.
- Face recognition or identifying residents from video. Each room or camera is linked to a resident by configuration.

## 6. System overview

Five stages (see the diagram):

1. **Capture (inside the privacy boundary).** A webcam or phone looks down on a kitchenette.
   - MediaPipe turns each frame into a body skeleton.
   - A custom-trained **Roboflow** detector finds task objects: kettle, cup, teabag, spoon, milk, sugar, and optionally hands and a "pouring" class.
   - Frames are dropped after processing. Only skeletons, object boxes and timestamps go downstream.
2. **Understand.**
   - **Step recogniser:** state rules over object and hand interactions produce timestamped step events with confidence scores.
   - **Vision-LLM verifier (Gemini):** used only when confidence is low or an error is about to be raised. It gets a short clip and the list of possible steps, and returns which step happened and with what object.
   - **Task-graph tracker:** compares the events against the task's dependency graph.
   - **Error classifier:** applies the rules in §7.
3. **Learn normal.**
   - Every session, step and error is stored in **Tiger Data**.
   - A personal baseline per resident per task covers error score, step durations and gaps between steps.
   - A change detector compares each new session against that baseline.
4. **Explain and alert.**
   - An LLM (Claude) writes the plain-language summary **using only the detected evidence**, never adding anything of its own.
   - It suggests checks: infection or UTI, hydration, new medication, run the CAM screen.
   - Alerts are routed to the dashboard through **Supabase Realtime**, optionally with a phone push.
5. **Care team UI.** Live task map, evidence view, ghost replay, heat calendar and feedback. Feedback is logged in Langfuse and used to tune thresholds.

**Decision: custom detector plus a vision LLM, not either alone.**
- The detector gives fast, consistent, offline-capable results. That makes the demo safe, and it counts as a model we trained.
- The vision LLM handles ambiguous cases and generates descriptions.
- HelpMeOut (arXiv, Oct 2026) shows that frontier LLMs alone are poor at monitoring for errors. Our pitch is that **structure plus a personal baseline beats a bare LLM**.
- Do **not** train an action-recognition model from scratch, and do not depend on Isaac 0.5 (36B, too heavy).

## 7. Error model

### Task graph
- Each task is a graph of required **dependencies**, not a fixed sequence. Example: "teabag in cup" must happen before "pour," but "fill kettle" and "get cup" can happen in either order.
- Each step lists its **allowed objects** (spoon or teaspoon both count) and whether it is **optional** (milk and sugar are).

### Error types
| Type | Rule |
|---|---|
| **Omission** | A required step never happens before a step that depends on it, or before the task ends. |
| **Sequence** | A step happens before something it depends on, and that dependency is then done later. |
| **Perseveration** | A step meant to happen once happens again after other steps in between. |
| **Substitution** | The correct action is done with an object not on the allowed list. |
| **Hesitation** | A step or gap takes more than about 2.5 standard deviations longer than **this resident's** own average. |
| **Abandonment** | The task starts, then there are no events for N minutes before it completes. |

### Not counted as errors
- Valid alternative orders and skipped optional steps.
- Mistakes the resident fixes within a short window. Log these as a **self-corrected slip**, a weaker signal.
- Sessions where a second person (staff) is in frame. Mark these "assisted" and exclude them.
- Events with confidence below about 0.6 that the verifier can't resolve. Mark them **unclear**, never count them as errors.

These categories come from neuropsychology research on everyday-action errors, also used by the HelpMeOut benchmark and occupational therapists' standard assessments.

### From errors to a flag
- **Session score:** a weighted sum of errors. Omission and substitution weigh the most, hesitation the least. The weights are hand-set for the MVP.
- **Possible delirium flag:** **two or more sessions above the baseline threshold within 24–48 h**. A single bad session never alerts.
- **Slow drift:** a sustained upward trend over weeks, reported as a trend for review, not as an urgent alert.
- **Every alert includes:** the errors with timestamps, evidence clips or skeleton replays, the baseline comparison (for example "3 errors vs 0.2/day normal"), any care-record context, and suggested checks.
- **Calibration:** nurse feedback updates per-resident thresholds. For the MVP, just log it and show that it changes the threshold.

## 8. Data

- **Synthetic residents:** 3–5 residents with about 14 days of history each. Most are normal; one shows a sudden spike, one a slow drift.
  - Synthetic error rates should be realistic. Use the per-category rates from the HelpMeOut and neuropsychology papers.
- **Live session:** a teammate makes tea on stage, and the result is added to the demo resident's history.
- **Detector training data:** 10–15 clips filmed in a setup like the demo's, with about 200–400 labelled frames.
- **Care-record context:** synthetic medication changes, temperatures and fluid intake.
- **Retention:** store skeleton and object-event data only, never raw video. For evidence clips, store skeleton replays, or blurred clips if absolutely needed. This is a deliberate privacy decision to state in the pitch.

## 9. Screens

1. **Unit overview:** list of residents with a status chip (normal / watch / flagged) and a sparkline of their error score.
2. **Resident detail:**
   - Baseline chart with today's point.
   - Heat calendar.
   - Session list.
   - Context timeline (meds, temperature).
3. **Live session:** skeleton view next to the task-graph map. Steps turn green as they're completed; errors flash red (omission) or amber (repeat or sequence).
4. **Alert / evidence view:**
   - Plain-language summary.
   - Error list with timestamps, each opening its replay.
   - Ghost replay.
   - Suggested checks.
   - Confirm / false-alarm buttons.

**Design priorities:** a nurse should understand an alert **in 10 seconds**, it must be visual first, and the evidence must always be one tap away.

## 10. Demo script (≈3 min)

1. **Hook (20 s):** delirium is common, often missed, and frequently signals an infection. Nurses can't watch everyone.
2. **Baseline (30 s):** the dashboard shows Mrs. K's two normal weeks.
3. **Live (60 s):** a teammate makes tea, skips the teabag and pours twice. The task map flashes red and amber in real time.
4. **Alert (30 s):** her sparkline spikes, the second qualifying session triggers the flag, and the nurse's phone or dashboard alerts.
5. **Why (30 s):** open the evidence: exact errors, ghost replay against her normal, and "new antibiotic started 2 days ago; check for UTI or dehydration."
6. **Close (10 s):** privacy (no video stored), feedback loop, and what it builds on.

**Fallback:** a pre-recorded session that runs through the same pipeline, in case the camera or Wi-Fi fails. The verifier must handle being offline gracefully.

## 11. Positioning and prior art (be upfront with judges)

| Work | What it does | How we differ |
|---|---|---|
| **CHEF-VL** (WashU, UbiComp 2026) | Detects cooking-sequence errors with a vision-language model. | We turn the detector into an early-warning signal for staff, using a personal baseline. |
| **RegulAR** (arXiv Aug 2026) | AR task graph plus a multimodal AI that detects errors and helps the user recover. | Aimed at the person doing the task; ours is aimed at nurses, over time. |
| **HelpMeOut** (arXiv Oct 2026) | Benchmark showing LLMs are poor error monitors. | Motivates our structured design. |
| **COACH**, egg-boiling "cognitive prosthesis" study | Guide dementia patients through tasks. | Ours does no guidance; it's about detecting change. |
| **Teton**, Inspiren AUGi, AltumView | Commercial skeleton-only care monitoring, focused on falls. | Different signal (task errors) and condition (delirium). |
| **Edinburgh FEATHER**; smart-home delirium/UTI papers | Detect delirium or UTI from passive home sensors. | We use task-level errors as the signal, and give evidence per alert. |
| Hackathon projects: AURA, Vigil, Cognuance, MemoryMesh, Buddy, Granny Guard | Nearby ideas (eye tracking, wakefulness, quiz-based trends, camera assistants). | None combines task errors, a personal baseline and a delirium alert. |

**What's new is the combination:** step-level tracking of real tasks, a personal baseline, a sudden-change delirium alert for care staff, and evidence behind every flag. The detector alone is not new; say so.

## 12. Responsible design

- Skeleton-only processing, no stored video, no face identification.
- Flags for review, **never a diagnosis**, with that wording kept consistent everywhere.
- The LLM summary may only restate detected evidence. No speculation and no medical advice beyond standard check prompts.
- Show uncertainty: "unclear" events, and confidence on each alert.
- Consent: the resident or their substitute decision-maker opts in, and the system is per room and can be turned off.
- Bias and limits: pose estimation is less accurate with walkers or wheelchairs and for unusual postures. State this, and treat low-confidence sessions as unclear rather than as errors.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Detector unreliable under venue lighting | Train on clips filmed in demo-like conditions; bring a lamp; keep the pre-recorded fallback. |
| Verifier latency or network failure | Call it only on uncertain or error moments; cache results; work offline in degraded mode. |
| False alerts in the live demo | Script the demo; hand-tune thresholds on synthetic history; require two sessions to alert. |
| Judges see "another dementia camera" | Lead with delirium and sudden change, nurse-facing evidence, and the prior-art table. |
| Scope creep | Ship the MVP list before anything from Nice to have. |

## 14. Open questions

- Hackathon dates, team size and roles: not yet confirmed.
- Whether the rules let one project enter several sponsor and MLH prizes, and whether there's a cap.
- What the Papiers.ai challenge requires.
- Final product name and domain.
- Whether the vision verifier is Gemini only, or also Claude, given the Gemini prize.

## 15. Notes for the next agent

- Ian prefers concise answers, visual-first output, honest prior-art checks, and discussing plans before building.
- On Discord: no tables (use bullet lists), and send images as attachments.
- The YC student credits available are Supabase, Roboflow, Anthropic, OpenAI, Google/Gemini, AWS, Langfuse, Deepgram, Vapi, Tavus, Browser Use, Firecrawl, AgentMail and Blaxel. Of these, the spec uses only Roboflow, Supabase, Anthropic, Gemini, Langfuse and optionally AWS.

---

## 16. Architecture decisions (locked)

Diagrams: `docs/routine-watch-architecture.png` (components), `docs/routine-watch-flow.png` (process flow).

- **Single capture stream.** The capture process emits one JSONL record per frame (skeleton + hand landmarks + object boxes + timestamp). Live camera, the pre-recorded fallback, tests and scenarios all feed the pipeline through this same format.
- **A. Verifier privacy:** only on low-confidence/pre-error moments, send Gemini 4–8 low-res frames cropped to the counter (no face), from a ~5 s in-memory ring buffer. Never stored. Timeout ~3 s → event marked `unclear`.
- **B. Alerts:** the FastAPI WebSocket that carries the live view also carries alerts. Supabase is optional, only for phone push later.
- **C. Placement:** the whole pipeline (capture → recogniser → task graph → errors → session score) runs on the demo laptop and works offline. It uplinks events, sessions and downsampled skeletons to the backend on Vultr (FastAPI + baseline/change detection + alert builder + dashboard), which stores in Tiger Data.
- **Roboflow:** detector runs locally from downloaded weights. No hosted inference. Humans run training (max 2–3 runs, 50 credits/month).
- **Hands:** use MediaPipe hand landmarks as well as pose; task steps are hand–object interactions.
