# ExpertWiki Admission Gate

Use this gate separately for every candidate file and every distinct evidence
passage inside a mixed file. The gate determines whether the material deserves
preservation as an accepted source and synthesis into a knowledge card.

## Admit When

Admit a file when it contains one or more of these signals and the source origin
is identifiable:

- A human explicitly agrees, rejects, questions, requests a change, or identifies
  a risk or infeasible approach.
- Expert feedback from code review, design review, requirements review, an
  incident postmortem, testing, launch, or user feedback.
- A trace of a human changing AI output, including what changed, why, and what
  problem the change solved.
- An observed result such as a passing test, production failure, user
  acceptance, rollout, adoption, or a measurable outcome.
- A decision rationale based on security, performance, cost, compliance, user
  experience, maintainability, or a business objective.
- A failure, rejected recommendation, counterexample, or boundary condition.
- Enough context to interpret the evidence: project type, stack, task, goal,
  constraints, role, version, or time.

## Reject When

Reject the candidate from knowledge extraction when any of these is true and no
stronger evidence appears elsewhere in the same file:

- It is only an AI-generated summary or conclusion with no human confirmation.
- It is a context-free prompt trick or generic instruction.
- It is casual conversation, greeting, emotional expression, or social filler.
- It is an unsupported personal assertion.
- It is duplicate content, template language, or automatic log noise.
- The origin cannot be distinguished as human, AI, or observed system output.
- It reports success without the basis, context, or result.

## Evidence Classification

Record the strongest defensible confidence, not the most optimistic one:

| Confidence | Use when |
| --- | --- |
| `single_case` | One contextualized case or decision is documented. |
| `multiple_confirmed` | More than one person or case confirms the pattern. |
| `verified` | A repeatable test, production result, or other direct validation supports it. |
| `stale` | The evidence was once useful but the version, context, or result may no longer hold. |
| `disputed` | Credible evidence or reviewers disagree. |

If the file contains useful context but no admissible evidence, preserve no
knowledge card and report `rejected: insufficient human-confirmed evidence`.

When a file mixes admissible evidence with chat filler, AI-only prose, or
automatic noise, preserve the file only as provenance if needed, but extract
only the admitted passages into the card. Do not let surrounding text increase
the confidence of an admitted claim.

## Extraction Record

For each admitted file, capture:

```text
source: <local source path>
decision: admitted | rejected
signals: <which admission signals were present>
origin: human | mixed | observed | unknown
confidence: <one allowed confidence state>
reason: <one sentence grounded in the file>
```

Do not infer a human decision from tone, formatting, file location, or the mere
presence of an AI transcript. If the evidence is ambiguous, reject it or ask
the user for provenance.
