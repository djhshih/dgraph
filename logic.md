
```{GBNF}
root    ::=  expr

expr    ::=  word+ (op word+)+

op      ::=  " and " | " or "

word  ::=  [a-zA-Z][a-zA-Z0-9_+-]*
```

*Note*: `word` matches non-greedily.

