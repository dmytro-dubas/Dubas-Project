from __future__ import annotations
from pathlib import Path
import sys
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken
from . import ast as A
from .span import SourceSpan

if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)


def _load_grammar() -> str:
    repo_path = Path(__file__).resolve().parent.parent.parent / "grammar" / "sipl.lark"
    if repo_path.is_file():
        return repo_path.read_text(encoding="utf-8")
    pkg_path = Path(__file__).with_name("sipl.lark")
    if pkg_path.is_file():
        return pkg_path.read_text(encoding="utf-8")
    try:
        import importlib.resources as pkg_resources
        res = pkg_resources.files("sipl").joinpath("sipl.lark")
        if res.is_file():
            return res.read_text(encoding="utf-8")
    except Exception:
        pass
    raise FileNotFoundError("Граматику sipl.lark не знайдено.")


_GRAMMAR = _load_grammar()
_LARK = Lark(_GRAMMAR, parser="lalr", propagate_positions=True)
_LARK_CST = Lark(_GRAMMAR, parser="lalr", propagate_positions=True, keep_all_tokens=True)


class SIPLSyntaxError(Exception):
    def __init__(self, msg: str, line: int, col: int, src_line: str):
        super().__init__(msg)
        self.msg = msg
        self.line = line
        self.col = col
        self.src_line = src_line

    def render(self) -> str:
        return (f"Синтаксична помилка ({self.line}:{self.col}): {self.msg}\n"
                f"  {self.src_line}\n  {' ' * (self.col - 1)}^")


def _sp(m) -> SourceSpan:
    return SourceSpan.from_meta(m)


@v_args(meta=True, inline=True)
class _ToAST(Transformer):
    def program(self, m, b):
        return A.Program(b, span=_sp(m))

    def seq(self, m, a, b):
        return A.Seq(a, b, span=_sp(m))

    def assign(self, m, n, e):
        return A.Assign(str(n), e, span=_sp(m))

    def skip(self, m):
        return A.Skip(span=_sp(m))

    def ite(self, m, c, t, e):
        return A.If(c, t, e, span=_sp(m))

    def loop(self, m, c, b):
        return A.While(c, b, span=_sp(m))

    def block(self, m, b):
        return A.Block(b, span=_sp(m))

    def num(self, m, t):
        return A.Num(int(t), span=_sp(m))

    def var(self, m, t):
        return A.Var(str(t), span=_sp(m))

    def add(self, m, l, r):
        return A.BinOp("+", l, r, span=_sp(m))

    def sub(self, m, l, r):
        return A.BinOp("-", l, r, span=_sp(m))

    def mul(self, m, l, r):
        return A.BinOp("*", l, r, span=_sp(m))

    def true(self, m):
        return A.BoolConst(True, span=_sp(m))

    def false(self, m):
        return A.BoolConst(False, span=_sp(m))

    def rel(self, m, l, op, r):
        return A.Rel(str(op), l, r, span=_sp(m))

    def neg(self, m, x):
        return A.Not(x, span=_sp(m))

    def conj(self, m, l, r):
        return A.Logic("and", l, r, span=_sp(m))

    def disj(self, m, l, r):
        return A.Logic("or", l, r, span=_sp(m))


_TOKEN_NAMES = {
    "SEMICOLON": "';'",
    "COLONEQUAL": "':='",
    "LPAR": "'('",
    "RPAR": "')'",
    "PLUS": "'+'",
    "MINUS": "'-'",
    "STAR": "'*'",
    "REL": "оператор відношення",
    "NAME": "ім'я змінної",
    "NUMBER": "число",
    "$END": "кінець програми",
}


def _token_name(name: str) -> str:
    if name in _TOKEN_NAMES:
        return _TOKEN_NAMES[name]
    return f"'{name.lower()}'"


def _to_error(e: UnexpectedInput, text: str) -> SIPLSyntaxError:
    lines = text.splitlines() or [""]
    line = e.line if getattr(e, "line", -1) > 0 else len(lines)
    col = e.column if getattr(e, "column", -1) > 0 else len(lines[-1]) + 1
    if isinstance(e, UnexpectedCharacters):
        msg = f"неочікуваний символ {text[e.pos_in_stream]!r}"
    elif isinstance(e, UnexpectedToken):
        tok_type = getattr(e.token, "type", None)
        tok_val = str(e.token)
        if tok_type == "$END" or tok_val in ("", "$END"):
            msg = "неочікуваний кінець програми, забули 'end'?"
        else:
            exp = ", ".join(sorted({_token_name(t) for t in e.expected}))
            msg = f"неочікуваний токен {tok_val!r}; очікувалось: {exp}"
    else:
        msg = "неочікуваний кінець програми, забули 'end'?"
    return SIPLSyntaxError(msg, line, col, lines[min(line, len(lines)) - 1])


def parse_tree(text: str, keep_tokens: bool = False):
    try:
        if keep_tokens:
            return _LARK_CST.parse(text)
        return _LARK.parse(text)
    except UnexpectedInput as e:
        raise _to_error(e, text) from None


def parse(text: str) -> A.Program:
    return _ToAST().transform(parse_tree(text))


def parse_file(path: str) -> A.Program:
    return parse(Path(path).read_text(encoding="utf-8"))
