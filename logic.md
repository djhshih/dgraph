
```{GBNF}
root    ::=  expr

expr    ::=  phrase op phrase

op      ::=  " and " | " or "

phrase  ::=  [a-zA-Z0-9 ]+
```

*Note*: `phrase` matches non-greedily.

