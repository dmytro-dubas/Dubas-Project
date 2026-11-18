from __future__ import annotations
import operator
from dataclasses import dataclass, field
from . import terms as T

State = dict[str, int]

BIN = {
    "add": operator.add,
    "sub": operator.sub,
    "mult": operator.mul,
    "mul": operator.mul,
    "gr": operator.gt,
    "ls": operator.lt,
    "ge": operator.ge,
    "le": operator.le,
    "eq": operator.eq,
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
}


def fmt_state(st: State) -> str:
    return "[" + ", ".join(f"{k} -> {v}" for k, v in sorted(st.items())) + "]"


class StepLimitExceeded(Exception):
    pass


class UndefinedVariable(Exception):
    pass


@dataclass
class TraceStep:
    n: int
    rule: str
    detail: str
    before: State
    after: State


@dataclass
class EvalResult:
    status: str
    state: State | None
    trace: list[TraceStep] = field(default_factory=list)
    reason: str = ""


class Evaluator:
    def __init__(self, max_steps: int = 1000):
        self.max_steps = max_steps
        self.steps = 0
        self.trace: list[TraceStep] = []

    def value(self, t: T.Term, st: State):
        match t:
            case T.Const(value=v):
                return v
            case T.Den(var=x):
                if x not in st:
                    raise UndefinedVariable(f"змінна {x} не визначена у стані")
                return st[x]
            case T.S2(op=o, a=a, b=b):
                return BIN[o](self.value(a, st), self.value(b, st))
            case T.S1(op="neg" | "not", a=a):
                return not self.value(a, st)
        raise TypeError(f"не вираз: {t}")

    def run(self, term: T.Term, state: State) -> EvalResult:
        self.steps, self.trace = 0, []
        try:
            return EvalResult("defined", self._exec(term, dict(state)), self.trace)
        except StepLimitExceeded:
            return EvalResult("undefined", None, self.trace,
                              f"перевищено ліміт {self.max_steps} кроків, ймовірне зациклення")
        except UndefinedVariable as e:
            return EvalResult("undefined", None, self.trace, str(e))

    def _tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceeded

    def _log(self, rule: str, detail: str, before: State, after: State):
        self.trace.append(TraceStep(self.steps, rule, detail, dict(before), dict(after)))

    def _exec(self, t: T.Term, st: State) -> State:
        match t:
            case T.ID():
                self._tick()
                self._log("AF_ID", "ID", st, st)
                return st
            case T.AS(var=x, expr=e):
                self._tick()
                new = {**st, x: self.value(e, st)}
                self._log("AF_AS", f"{x} := {e}", st, new)
                return new
            case T.Comp(left=l, right=r):
                self._tick()
                self._log("AF_SEQ", f"{l} * {r}", st, st)
                return self._exec(r, self._exec(l, st))
            case T.IF(cond=c, then=a, orelse=b):
                self._tick()
                v = self.value(c, st)
                self._log("AF_IF_TRUE" if v else "AF_IF_FALSE", f"{c} = {v}", st, st)
                return self._exec(a if v else b, st)
            case T.WH(cond=c, body=b):
                k = 0
                while True:
                    self._tick()
                    v = self.value(c, st)
                    if not v:
                        self._log("AF_WH_FALSE", f"ітерація {k}: {c} = false", st, st)
                        return st
                    self._log("AF_WH_TRUE", f"ітерація {k}: {c} = true", st, st)
                    st = self._exec(b, st)
                    k += 1
        raise TypeError(f"не оператор-терм: {t}")
