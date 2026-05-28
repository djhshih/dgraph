```{GBNF}
root        ::= ws? expr ws?

expr        ::= or_expr
or_expr     ::= and_expr (op_or and_expr)*
and_expr    ::= item (op_and item)*
item        ::= grouped | phrase

grouped     ::= "(" ws? expr ws? ")"

op_or      ::= ws "or" ws
op_and     ::= ws "and" ws

phrase      ::= token (sep token)*
token       ::= [^()\n \t]+
sep         ::= [ \t]+ | "\n"

ws          ::= [ \t\n]*
```

Notes

- Logical structure is inferred conservatively from natural-language branch labels.
- Only explicit `and` and `or` introduce boolean operators.
- Newlines are formatting separators inside a phrase; they are not logical operators.
- Any text without explicit boolean operators is treated as a single atomic condition phrase.
- Parentheses may be used to disambiguate precedence when present.
- Operator precedence follows standard boolean convention: `and` binds tighter than `or`.
- Phrases may contain clinical shorthand and punctuation, including forms such as `HR+/HER2-`, `cN0/iN0`, `>=cT2`, `stage II-III`, `ACOSOG-Z0011`, and `gBRCA1/2-wt`.
- Qualifying text such as `at initial diagnosis`, `at primary diagnosis`, `after neoadjuvant ChT`, `before surgery`, `criteria met`, and `criteria not met` remains part of the same atomic phrase unless explicit boolean operators are present.
- Because branch labels are natural language, some expressions remain semantically ambiguous. For example, `gBRCA1/2m and stage III or high-risk non-pCR` can be parsed syntactically using precedence rules, but its intended clinical meaning may still require domain-specific normalization or upstream correction.
- Domain-specific shorthand expansion is outside this grammar. If desired, a later normalization step may map phrases such as `HR+/HER2-` to a more explicit logical form.
