# ShiftPlanner – Product Requirements Document
*v2 — February 2026*

---

## 1. Overview

A private, self-hosted scheduling system for coordinating work assignments across ~40 people. The system automatically generates conflict-free schedules from scratch and allows users to refine them through natural language — including voice memos.

The core question the system answers:

> *Who should do which task or coverage slot, when, where, and with which resources — while respecting real-world constraints?*

---

## 2. Core Concepts

### 2.1 People

The persistent pool of participants available for scheduling.

- **Skills / roles** — what a person is qualified to do (flat list; a person may have multiple)
- **Skill hierarchy** — a senior skill level can cover junior-level requirements (e.g. senior driver can fulfill a junior driver slot), but not vice versa
- **Availability** — when a person can be assigned, expressed as one of three states:
  - *Expected* — a predefined work shift; assignment is normal and expected
  - *Offered* — personal time the person has made available; assignment is permitted but subject to fairness
  - *Unavailable* — cannot be assigned under any circumstances
- **Limitations** — explicit exclusions independent of availability (e.g. cannot operate certain resources)
- **Maximum working hours** — per day and per planning period
- **Minimum rest period** — required gap between consecutive assignments

### 2.2 Shift Template

The predefined time structure for a planning period. Defines the canvas on which assignments are made.

- A **Shift** is a single named time block with a start time, end time, and day (e.g. Monday 08:00–10:00)
- A **Shift Template** is a reusable collection of shifts that defines the structure of a planning cycle
- Shift Templates can be saved and reapplied across planning cycles
- The planning horizon (daily, weekly, monthly, ad-hoc) is a parameter of the template, not a hardcoded concept

### 2.3 Tasks

Specific named deliverables to be completed during the planning period.

- **Required skills** — one or more skills needed to perform the task
- **Duration** — total hours required to complete the task
- **Splittable** — whether the task can be distributed across multiple non-consecutive shifts, or must be completed in one continuous block
- **Location** — physical location where the task takes place
- **Resources required** — shared resources needed (see 2.5)
- **Priority** — required vs. optional
- **Team size** — minimum and maximum number of people that can be assigned (default: exactly 1)
- **Dependencies** — a task may require another task to be completed first (ordering constraint)

### 2.4 Coverage Requirements

Abstract staffing demands that are not tied to a specific named task. Defines how many people with a given skill are needed during a given shift.

- **Shift** — which time block the requirement applies to
- **Required skill** — the skill the assigned people must have
- **Count** — minimum number of people needed (e.g. "at least 2 drivers on Monday morning")

Tasks and Coverage Requirements coexist in the same planning cycle and compete for the same pool of people. The solver satisfies both simultaneously.

### 2.5 Resources

Shared physical items required for some tasks or coverage slots. Resources are persistent across planning cycles — they do not need to be re-entered each time. Availability is binary per time window:

- *Available* — default state, no entry needed
- *Unavailable* — explicitly marked for a specific time window (e.g. vehicle in maintenance Tuesday–Wednesday)

Resources can only be assigned to one person at a time.

### 2.6 Schedule

The output of the solver: a conflict-free assignment of people to tasks and coverage slots across the planning period.

- Associates: Person → (Task or Coverage Slot) → Shift → Location → Resources
- The solver is the sole authority on schedule validity
- A schedule is always generated from scratch initially, then refined through subsequent re-solves

### 2.7 Locations and Travel

Physical locations associated with tasks and resources.

- Tasks have a location
- Travel time between locations is defined as a matrix (location A → location B = N minutes)
- Consecutive assignments for the same person at different locations must respect travel time as a buffer

---

## 3. Constraint Model

### Hard Constraints
*(schedule is invalid if any of these are violated)*

- No person assigned to overlapping tasks or coverage slots
- Skill matching — person must have the required skill (respecting skill hierarchy)
- Resource exclusivity — shared resources assigned to at most one person per time slot
- Availability — no assignment outside a person's available windows
- Maximum working hours — not exceeded per day or per planning period
- Minimum rest — required gap between consecutive assignments respected
- Travel time — sufficient buffer between consecutive assignments at different locations
- Task dependencies — dependent tasks scheduled after their prerequisites
- Team size — assignments within defined min/max headcount per task

### Soft Constraints
*(optimized; violations incur a weighted penalty)*

- Task priority — required tasks are fully satisfied before optional ones
- Coverage fulfillment — coverage requirements met as fully as possible
- Fairness — equalize the proportion of *Offered* time converted into assignments across people. Expected time is not subject to fairness balancing.
- Travel minimization — consecutive assignments prefer nearby locations
- Preference respect — soft availability preferences honored where possible
- Schedule stability — when re-solving, minimize disruption to previously published assignments

---

## 4. Initial Schedule Generation

Given a populated Shift Template, a set of people, tasks, and coverage requirements, the system generates a complete schedule from scratch. The solver attempts to satisfy all hard constraints and optimize soft constraints simultaneously.

When no feasible solution exists, the system reports which constraints are in conflict and suggests which could be relaxed to make the problem solvable.

---

## 5. Schedule Refinement

After an initial schedule is generated, users refine it through natural language. The refinement loop is:

1. **User input** — voice memo or typed natural language
2. **AI interpretation** — LLM transcribes and translates into structured constraint changes
3. **Confirmation** — AI summarizes what it understood and what will change, before applying
4. **Re-solve** — solver regenerates a valid schedule using the previous solution as a starting point, with locked assignments preserved
5. **Explanation** — system explains what changed, what was moved, and why
6. **Updated schedule** displayed

### Valid refinement operations (examples)
- Availability changes ("Alice can't work Thursday morning")
- Limitation changes ("Bob shouldn't use scooters")
- Task modifications ("this task now needs two people")
- Priority changes ("move task X to required")
- New tasks or coverage requirements added mid-cycle
- Locking specific assignments ("keep Alice on Monday morning regardless")
- Hypothetical queries ("what if Alice was unavailable all week?") — explored without committing

---

## 6. Explanation Layer

Every schedule — initial or refined — is accompanied by a structured explanation. Explanations are designed to be readable as spoken language, not just as structured data.

The explanation layer provides:

- **Summary of assignments** — who is doing what, when, and where
- **Constraint analysis** — which soft constraints were tight, relaxed, or violated and by how much
- **Per-person and per-task breakdown** — contribution of each entity to the overall score
- **Change diff** — after re-solving, what changed from the previous schedule and why
- **Infeasibility report** — when no valid schedule exists, which constraints conflict

---

## 7. Schedule Versioning

Named snapshots of schedules can be saved at any point. Users can compare versions, roll back to a previous version, and label versions (e.g. "Draft 1", "After Monday feedback", "Published").

---

## 8. User Interface

### Input Modes

The system supports two equally valid ways to make changes — users can use either or both interchangeably:

- **Natural language** — voice memo or typed input, interpreted by the AI assistant, confirmed before applying, followed by a re-solve and explanation
- **Manual editing** — direct editing of people, tasks, availability, resources, coverage requirements, and shift templates through structured UI forms and editors

Both input modes trigger the same underlying flow: data changes → re-solve → updated schedule. The solver does not distinguish between the origin of a change.

### Views

- **Schedule View** — calendar-based, toggleable between per-person and per-task perspectives. Shows conflicts, warnings, and coverage gaps visually.
- **People Editor** — manage people, skills, availability, and limitations
- **Task Editor** — manage tasks, requirements, dependencies, and priorities
- **Coverage Editor** — manage coverage requirements per shift
- **Shift Template Editor** — define and save shift structures
- **Chat / Voice Panel** — primary natural language interaction surface
- **Explanation Panel** — displays explanation after each solve

### Manual Overrides

Users can lock specific assignments directly in the schedule view. Locked assignments are preserved across re-solves. The solver validates and warns if manual overrides conflict with hard constraints.

---

## 9. Dual Scheduling Contexts

The three availability states (Expected, Offered, Unavailable) make the system context-agnostic:

- **Collaboration week** — predefined work shifts are Expected, free time that can be used is Offered, personal off-limits time is Unavailable
- **Ongoing daily operations** — self-reported hours are Offered, everything else is Unavailable

The same system and solver handles both scenarios without configuration changes.

---

## 10. Privacy and Deployment

- Fully self-hosted on private infrastructure
- Private database — no personal or scheduling data leaves the deployment environment
- The AI assistant layer calls the Anthropic Claude API — the only external dependency
- No analytics, telemetry, or third-party services beyond the LLM API
