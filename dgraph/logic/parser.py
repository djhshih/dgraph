from dataclasses import dataclass
import os

from .ast import And, Expr, Group, Or, Phrase, PrefixCompare


def _debug(*args, **kwargs) -> None:
    if os.environ.get("DEBUG"):
        print(*args, **kwargs)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


class LogicSyntaxError(ValueError):
    pass


_COMPARE_START = set("><")
_BOUNDARY_CHARS = " \t\r\n()"


def _split_phrase_words(text: str) -> list[str]:
    return [part for part in text.split() if part]


def _tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t\r":
            i += 1
            continue
        if c == "\n":
            tokens.append(Token("LINE_OR", "\n"))
            i += 1
            continue
        if c == "(":
            tokens.append(Token("LPAREN", c))
            i += 1
            continue
        if c == ")":
            tokens.append(Token("RPAREN", c))
            i += 1
            continue
        if text.startswith(">=", i):
            tokens.append(Token("GE", ">="))
            i += 2
            continue
        if text.startswith("<=", i):
            tokens.append(Token("LE", "<="))
            i += 2
            continue
        if c == ">":
            tokens.append(Token("GT", ">"))
            i += 1
            continue
        if c == "<":
            tokens.append(Token("LT", "<"))
            i += 1
            continue
        if text.startswith("and", i) and _is_word_boundary(text, i - 1) and _is_word_boundary(text, i + 3):
            tokens.append(Token("AND", "and"))
            i += 3
            continue
        if text.startswith("or", i) and _is_word_boundary(text, i - 1) and _is_word_boundary(text, i + 2):
            tokens.append(Token("OR", "or"))
            i += 2
            continue

        start = i
        j = i
        while j < n:
            if text[j] in "()\n":
                break
            if text.startswith(">=", j) or text.startswith("<=", j) or text[j] in _COMPARE_START:
                break
            if text.startswith("and", j) and _is_word_boundary(text, j - 1) and _is_word_boundary(text, j + 3):
                break
            if text.startswith("or", j) and _is_word_boundary(text, j - 1) and _is_word_boundary(text, j + 2):
                break
            j += 1

        for word in _split_phrase_words(text[start:j]):
            tokens.append(Token("PHRASE", word))
        i = j
        _debug("---------------")
        _debug(f"text: {text}")
        _debug(f"tokens: {tokens}")
        
    return _insert_implicit_ops(tokens)


def _insert_implicit_ops(tokens: list[Token]) -> list[Token]:
    out: list[Token] = []
    prev: Token | None = None
    pending_compare: str | None = None
    for token in tokens:
        if token.kind in {"GE", "GT", "LE", "LT"}:
            pending_compare = token.kind
        elif token.kind == "PHRASE" and pending_compare is not None:
            if out and out[-1].kind == pending_compare:
                out.append(Token("PHRASE", token.value))
                pending_compare = None
                prev = token
                continue
            pending_compare = None
        else:
            pending_compare = None

        if token.kind == "LINE_OR":
            if prev is None or prev.kind in {"OR", "AND", "LPAREN", "LINE_OR"}:
                continue
            out.append(token)
            prev = token
            continue
        if prev is not None and _needs_implicit_and(prev, token):
            out.append(Token("AND", "and"))
        out.append(token)
        prev = token
    while out and out[-1].kind == "LINE_OR":
        out.pop()
    _debug(f"out: {out}")
    return out


def _needs_implicit_and(prev: Token, current: Token) -> bool:
    left = prev.kind in {"PHRASE", "RPAREN"}
    right = current.kind in {"PHRASE", "LPAREN", "GE", "GT", "LE", "LT"}
    return left and right


def _is_word_boundary(text: str, index: int) -> bool:
    if index < 0 or index >= len(text):
        return True
    return text[index] in _BOUNDARY_CHARS


class _Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Expr:
        if not self.tokens:
            raise LogicSyntaxError("empty expression")
        expr = self.parse_or()
        if self.pos != len(self.tokens):
            raise LogicSyntaxError(f"unexpected token: {self.tokens[self.pos].value!r}")
        return expr

    def parse_or(self) -> Expr:
        expr = self.parse_and()
        while self._accept_any("OR", "LINE_OR"):
            rhs = self.parse_and()
            expr = Or(expr, rhs)
        return expr

    def parse_and(self) -> Expr:
        expr = self.parse_compare()
        while self._accept("AND"):
            rhs = self.parse_compare()
            expr = And(expr, rhs)
        return expr

    def parse_compare(self) -> Expr:
        prefix_op = self._accept_compare_op()
        if prefix_op is not None:
            token = self._expect("PHRASE")
            return self._parse_prefix_compare(prefix_op, token.value)
        return self.parse_item()

    def _parse_prefix_compare(self, op: str, text: str) -> PrefixCompare:
        parts = [text]
        while self.pos < len(self.tokens) and self.tokens[self.pos].kind == "PHRASE":
            parts.append(self.tokens[self.pos].value)
            self.pos += 1
        if not parts:
            raise LogicSyntaxError("prefix comparison requires an attribute phrase")
        if len(parts) >= 2 and _looks_like_literal(parts[0]):
            return PrefixCompare(op, Phrase(parts[0]), Phrase(" ".join(parts[1:])))
        return PrefixCompare(op, None, Phrase(" ".join(parts)))

    def parse_item(self) -> Expr:
        if self._accept("LPAREN"):
            expr = self.parse_or()
            self._expect("RPAREN")
            return Group(expr)
        token = self._expect("PHRASE")
        return Phrase(token.value)

    def _accept(self, kind: str) -> bool:
        if self.pos < len(self.tokens) and self.tokens[self.pos].kind == kind:
            self.pos += 1
            return True
        return False

    def _accept_any(self, *kinds: str) -> bool:
        if self.pos < len(self.tokens) and self.tokens[self.pos].kind in kinds:
            self.pos += 1
            return True
        return False

    def _accept_compare_op(self) -> str | None:
        for kind, value in (("GE", ">="), ("GT", ">"), ("LE", "<="), ("LT", "<")):
            if self._accept(kind):
                return value
        return None

    def _expect(self, kind: str) -> Token:
        if self.pos >= len(self.tokens):
            raise LogicSyntaxError(f"expected {kind}, got end of input")
        token = self.tokens[self.pos]
        if token.kind != kind:
            raise LogicSyntaxError(f"expected {kind}, got {token.kind}")
        self.pos += 1
        return token


def _looks_like_literal(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        try:
            float(text)
            return True
        except ValueError:
            return False


def parse(text: str) -> Expr:
    return _Parser(_tokenize(text)).parse()
