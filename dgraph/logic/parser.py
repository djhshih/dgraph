from dataclasses import dataclass

from .ast import And, Expr, Group, Or, Phrase, PrefixCompare


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


class LogicSyntaxError(ValueError):
    pass


def _tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
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

        j = i
        while j < n and text[j] not in "()":
            j += 1
        chunk = text[i:j]

        k = 0
        while k < len(chunk):
            if chunk[k] in " \t\r\n":
                k += 1
                continue
            if chunk.startswith(">=", k):
                tokens.append(Token("GE", ">="))
                k += 2
                continue
            if chunk.startswith("<=", k):
                tokens.append(Token("LE", "<="))
                k += 2
                continue
            if chunk[k] == ">":
                tokens.append(Token("GT", ">"))
                k += 1
                continue
            if chunk[k] == "<":
                tokens.append(Token("LT", "<"))
                k += 1
                continue
            if chunk.startswith("and", k) and _is_word_boundary(chunk, k - 1) and _is_word_boundary(chunk, k + 3):
                tokens.append(Token("AND", "and"))
                k += 3
                continue
            if chunk.startswith("or", k) and _is_word_boundary(chunk, k - 1) and _is_word_boundary(chunk, k + 2):
                tokens.append(Token("OR", "or"))
                k += 2
                continue
            start = k
            while k < len(chunk):
                if chunk.startswith(">=", k) or chunk.startswith("<=", k) or chunk[k] in "><":
                    break
                if chunk[k] in " \t\r\n":
                    look = k
                    while look < len(chunk) and chunk[look] in " \t\r\n":
                        look += 1
                    if chunk.startswith("and", look) and _is_word_boundary(chunk, look - 1) and _is_word_boundary(chunk, look + 3):
                        break
                    if chunk.startswith("or", look) and _is_word_boundary(chunk, look - 1) and _is_word_boundary(chunk, look + 2):
                        break
                k += 1
            phrase = " ".join(chunk[start:k].split())
            if phrase:
                tokens.append(Token("PHRASE", phrase))
        i = j
    return tokens


def _is_word_boundary(text: str, index: int) -> bool:
    if index < 0 or index >= len(text):
        return True
    return text[index] in " \t\r\n()"


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
        while self._accept("OR"):
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
        parts = text.split()
        if not parts:
            raise LogicSyntaxError("prefix comparison requires an attribute phrase")
        if len(parts) >= 2 and _looks_like_literal(parts[0]):
            return PrefixCompare(op, Phrase(parts[0]), Phrase(" ".join(parts[1:])))
        return PrefixCompare(op, None, Phrase(text))

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
