# Limitations

Condition inference is limited by ambiguity or oddity in natural language.
For example,

- '/' is used ambiguously. It functions as a separator. Sometimes it behaves like
  an 'and' operator and sometimes as an 'or' operator.
  For example, "HR+/HER2-" refers to breast cancers that are both "HR+" *and*
  "HER2-". "cN0/iN0" refers to absence of lymph node spread by clinical (c)
  *or* imaging (i) assessment.

- Natural language can express eligibility criteria in terms of a set membership
  expression. The conjunction 'and' can mean 'logical and', but it can also mean 'union' of 
  two sets.
  For example, in "premenopausal patients receiving OFS and postmenopausal
  patients", "and" functions as a "union" operator between two sets:
  1) "premenopausal patients receiving OFS"
  2) "postmenopausal patients".
  When we convert this set membership expression into a logical expression for
  selection, we translate "and" as "or" (as well as inserting an implicit "and"):
  patient must satisfy the condition: ("premenopausal" and "receiving OFS") or
  "postmenopausal".

