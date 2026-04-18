---
name: review-skill
description: >
  Reviews, audits, and scores skill files (SKILL.md) for quality,
  completeness, frontmatter correctness, discoverability, and
  anti-patterns. Use when asked to review, audit, check, or improve
  a skill file, or when a user says "is this skill good?", "check my
  skill", or pastes a SKILL.md for feedback. Also use proactively
  after writing a new skill — self-apply as a final quality gate.
  Don't use for reviewing general Markdown documentation, README
  files, or code files that are not skill definitions.
argument-hint: "Optional: skill name or path. Omit to audit all discovered skills."
metadata:
  version: "1.0"
---

# Review Skill

Audit `SKILL.md` files against the [Agent Skills specification](https://agentskills.io/specification) and produce a scored Markdown report.

## Guardrails

- Only review `SKILL.md` files — not general Markdown, READMEs, or code.
- Collect **all** discovered skills before reviewing any.
- This skill can review itself as a smoke test.

## Step 1: Discovery

If the user provided a specific skill name or path, review only that
skill and skip the search below.

Otherwise search every location:

| Priority | Location             | Scope                                 |
| -------- | -------------------- | ------------------------------------- |
| 1        | `skills/`            | repo-level reference skills           |
| 2        | `.github/skills/`    | GitHub Copilot project skills         |
| 3        | `.agents/skills/`    | standardized agent skills (preferred) |
| 4        | `.claude/skills/`    | Claude agent skills                   |
| 5        | `~/.copilot/skills/` | user-level Copilot skills             |
| 6        | `~/.agents/skills/`  | user-level agent skills (preferred)   |
| 7        | `~/.claude/skills/`  | user-level Claude skills              |

A skill is a **subfolder** containing `SKILL.md` (preferred) or
`SKILLS.md` (non-standard — flag it). Loose `.md` files are not skills.

If the same skill name appears in multiple locations, report the
conflict and note which location wins at runtime (higher priority
number = lower precedence).

## Step 2: Review each skill

Apply every check below. Assign severity: **Error** (blocks correct
function), **Warning** (degrades quality or discoverability),
**Info** (style suggestion).

### File and folder

| Check                    | Pass condition              | Severity if failed |
| ------------------------ | --------------------------- | ------------------ |
| Skill in named subfolder | Not loose in skills root    | Error              |
| File named `SKILL.md`    | Exact match, case-sensitive | Warning            |
| Folder name format       | `[a-z0-9-]+` only           | Warning            |

### Frontmatter

Validate against the [Agent Skills specification](https://agentskills.io/specification).
Skills in agent-loaded locations (`.agents/`, `.github/`, `.copilot/`,
`.claude/`) **must** have frontmatter. Skills in a root `skills/`
folder intended as human-readable reference may omit it — note but
don't error.

**Errors** (block correct function):
- Frontmatter block missing (`---` delimiters not found) — Error for agent-loaded, Info for reference skills
- `name` does not match folder name exactly
- `description` missing or empty

**Warnings** (degrade quality):
- `description` under 20 chars
- `description` lacks searchable trigger phrases
- Unknown frontmatter fields (spec allows: `license`, `compatibility`, `metadata`, `allowed-tools`)

**Info:**
- No negative trigger ("Don't use when...") in description

### Body content

**Errors:**
- No numbered, actionable procedure steps
- `./path` references that don't resolve to a file

**Warnings:**
- Over 500 lines (recommend splitting to `references/`)
- Absolute paths (`/home/...`) instead of `./`
- Time-sensitive logic (hard-coded dates or version cutoffs)
- Future-tense only — has promises but no current steps

**Info:**
- Body opens with a "Purpose and contract" section instead of a brief orienting sentence or guardrails
- No guardrails section (if applicable)
- No output contract (if the skill produces artifacts)

### Quality and discoverability

- Would this description cause the agent to select the skill for the right tasks?
- Are procedures specific enough to produce consistent output across runs?
- Is bulk content pushed to `references/` rather than inline?
- Does the argument-hint (if declared) have corresponding branch logic in the procedure?

## Step 3: Anti-patterns

Flag if present — these are the most common skill authoring mistakes:

| Anti-Pattern           | Explanation                                       |
| ---------------------- | ------------------------------------------------- |
| Vague description      | "A helpful skill" — agent cannot route to it      |
| No negative trigger    | Adjacent tasks will false-positive                |
| Monolithic body        | Everything inline; no `references/` offload       |
| Missing procedure      | Preamble only, no actionable steps                |
| Unused declared fields | `argument-hint` in frontmatter, no branch in body |

## Step 4: Output

Produce a Markdown report:

```markdown
# Skill Review Report

## Summary

- Skills found: N
- Locations searched: [list]
- Issues: N errors, N warnings, N info

## Skills Reviewed

### `<folder-name>`

**Location**: `<relative path to SKILL.md>`
**Status**: ✅ Pass / ⚠️ Warnings / ❌ Errors

| Check               | Severity | Result | Note                                |
| ------------------- | -------- | ------ | ----------------------------------- |
| Folder naming       | —        | ✅     |                                     |
| File name           | Warning  | ⚠️     | Uses SKILLS.md                      |
| Frontmatter present | Error    | ❌     | No --- block                        |
| name matches folder | —        | N/A    | Cannot check (no frontmatter)       |
| description quality | Warning  | ⚠️     | 12 chars, too short                 |
| Negative trigger    | Info     | ℹ️     | Consider adding "Don't use when..." |
| Procedure present   | —        | ✅     |                                     |
| File length         | —        | ✅     | 94 lines                            |

**Recommendations** (ordered by severity):

1. ❌ Add YAML frontmatter with `name` and `description`
2. ⚠️ Rename `SKILLS.md` → `SKILL.md`
3. ⚠️ Expand description to include trigger phrases
4. ℹ️ Add a negative trigger to reduce false positives

---
```

If only one skill was reviewed (scoped run), omit the Summary section
and go straight to the skill block.
