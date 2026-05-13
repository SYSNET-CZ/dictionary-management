# Pipeline Routing

Hermes must automatically select a pipeline based on task intent.

## Default behavior

If no pipeline is specified, determine it from the task.

---

## Classification rules

### 1. Lite pipeline

Use when task contains:

* "fix"
* "bug"
* "small"
* "minor"
* "simple"
* "quick"

OR when task is clearly incremental and low-risk.

→ pipeline: lite

---

### 2. Full development pipeline

Use when task contains:

* "implement"
* "build"
* "add feature"
* "create"
* "extend"

→ pipeline: dev

---

### 3. Review pipeline

Use when task contains:

* "review"
* "check"
* "analyze"

→ pipeline: review

---

### 4. Critical audit pipeline

Use when task contains:

* "critical"
* "security"
* "stress"
* "failure"
* "edge case"

→ pipeline: critic

---

### 5. Architecture pipeline

Use when task contains:

* "design"
* "architecture"
* "system"
* "proposal"

→ pipeline: dev (Architect-first)

---

## Priority rules

If multiple matches:

1. critical > review > architecture > dev > lite

---

## Explicit override

If user specifies:

[pipeline:xyz]

→ ALWAYS use that pipeline

---

## Fallback

If classification is unclear:

→ use lite pipeline
