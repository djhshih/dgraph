```{GBNF}
root          ::= ws? expr ws?

expr          ::= or_expr
or_expr       ::= and_expr (or_op and_expr)*
and_expr      ::= cmp_expr (op_and cmp_expr)*
cmp_expr      ::= prefix_cmp | item
prefix_cmp    ::= cmp_op cmp_tail
cmp_tail      ::= value ws attr | attr
item          ::= grouped | phrase
value         ::= phrase
attr          ::= phrase
cmp_op        ::= ge_op | gt_op | le_op | lt_op

grouped       ::= "(" ws? expr ws? ")"

or_op         ::= ws "or" ws
op_and        ::= ws "and" ws
ge_op         ::= ws? ">=" ws?
gt_op         ::= ws? ">" ws?
le_op         ::= ws? "<=" ws?
lt_op         ::= ws? "<" ws?

phrase        ::= token (sep token)*
token         ::= [^()\n \t<>]+
sep           ::= [ \t]+ | "\n"

ws            ::= [ \t\n]*
```

Notes

- Logical structure is inferred conservatively from natural-language branch labels.
- Only explicit `and`, `or`, `>=`, `>`, `<=`, and `<` introduce operators.
- Newlines are formatting separators inside a phrase; they are not logical operators.
- Any text without explicit operators is treated as a single atomic condition phrase.
- Parentheses may be used to disambiguate precedence when present.
- Operator precedence is: comparison operators (`>=`, `>`, `<=`, `<`) bind tighter than `and`, which binds tighter than `or`.
- All comparisons use prefix form internally: `op value attr` or `op attr`.
- The `value` is optional because it may be embedded in the attribute phrase, for example `>= cT2`.
- Examples with explicit value: `> 2 positive_nodes`, `<= 3 positive nodes`.
- Examples with embedded value: `>= cT2`, `< pT1b`, `> 2 positive LNs` after appropriate normalization.
- In interpretation, prefix comparisons are compiled to typed predicates using `gt`, `ge`, `lt`, and `le`.
- When the value is omitted, interpretation attempts to infer it from the attribute phrase.
- Phrases may contain clinical shorthand and punctuation, including forms such as `HR+/HER2-`, `cN0/iN0`, `stage II-III`, `ACOSOG-Z0011`, and `gBRCA1/2-wt`.
- Qualifying text such as `at initial diagnosis`, `at primary diagnosis`, `after neoadjuvant ChT`, `before surgery`, `criteria met`, and `criteria not met` remains part of the same atomic phrase unless explicit operators are present.
- Because branch labels are natural language, some expressions remain semantically ambiguous. For example, `gBRCA1/2m and stage III or high-risk non-pCR` can be parsed syntactically using precedence rules, but its intended clinical meaning may still require domain-specific normalization or upstream correction.
- Domain-specific shorthand expansion is outside this grammar. If desired, a later normalization step may map phrases such as `HR+/HER2-` to a more explicit logical form.
