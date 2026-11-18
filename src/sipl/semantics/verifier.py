from __future__ import annotations
import ast as pyast
import itertools
import json
import math
from dataclasses import dataclass, field
from .. import ast as A
from .builder import build_term, build_bexp
from .evaluator import Evaluator, State
from . import terms as T

def _fib(n: int) -> int:
    if n <= 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


FUNCS = {
    "fact": lambda n: math.factorial(n) if n >= 0 else 0,
    "dfact": lambda n: 1 if n in (0, -1) else math.prod(range(n, 0, -2)),
    "pow": lambda x, y: x ** y if y >= 0 else 0,
    "gcd": lambda a, b: math.gcd(a, b),
    "fib": _fib,
    "isqrt": lambda n: math.isqrt(n) if n >= 0 else 0,
}
_ALLOWED = (
    pyast.Expression, pyast.BoolOp, pyast.And, pyast.Or, pyast.BinOp, pyast.Add, pyast.Sub,
    pyast.Mult, pyast.FloorDiv, pyast.Mod, pyast.UnaryOp, pyast.Not, pyast.USub, pyast.Compare,
    pyast.Eq, pyast.NotEq, pyast.Lt, pyast.LtE, pyast.Gt, pyast.GtE, pyast.Name, pyast.Load,
    pyast.Constant, pyast.Call
)


class Formula:
    def __init__(self, src: str):
        self.src = src
        tree = pyast.parse(src, mode="eval")
        self.vars: set[str] = set()
        for n in pyast.walk(tree):
            if not isinstance(n, _ALLOWED):
                raise ValueError(f"недозволена конструкція у формулі {src!r}: {type(n).__name__}")
            if isinstance(n, pyast.Call) and not (isinstance(n.func, pyast.Name) and n.func.id in FUNCS and not n.keywords):
                raise ValueError(f"недозволений виклик у формулі {src!r}")
            if isinstance(n, pyast.Constant) and not isinstance(n.value, (int, bool)):
                raise ValueError(f"недозволена константа у формулі {src!r}")
            if isinstance(n, pyast.Name) and n.id not in FUNCS:
                self.vars.add(n.id)
        self._code = compile(tree, "<spec>", "eval")

    def __call__(self, st: State):
        try:
            return eval(self._code, {"__builtins__": {}}, {**FUNCS, **st})
        except NameError as e:
            raise ValueError(f"невідома змінна у формулі '{self.src}': {e}") from e
        except (ValueError, OverflowError, ZeroDivisionError):
            return False


@dataclass
class Spec:
    inputs: list[str]
    pre: Formula
    invariant: Formula
    post: Formula
    domains: dict[str, tuple[int, int]]
    variant: Formula | None = None
    ghosts: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        if not self.domains:
            raise ValueError("області значень domains не можуть бути порожніми")
        for var, rng in self.domains.items():
            if len(rng) != 2 or rng[0] > rng[1]:
                raise ValueError(f"некоректний діапазон для '{var}': {rng}, очікується [min, max], де min <= max")
        for inp in self.inputs:
            if inp not in self.domains:
                raise ValueError(f"вхідна змінна '{inp}' відсутня у domains")
        pre_missing = self.pre.vars - set(self.inputs)
        if pre_missing:
            raise ValueError(f"передумова pre містить змінні {sorted(pre_missing)}, які відсутні у списку inputs: {self.inputs}")
        for g, src in self.ghosts.items():
            if src not in self.inputs:
                raise ValueError(f"ghost-змінна '{g}' посилається на невідомий вхід '{src}'")
            if g not in self.domains:
                raise ValueError(f"ghost-змінна '{g}' відсутня у domains")

        allowed_vars = set(self.domains.keys())
        for f_name, f in [("pre", self.pre), ("invariant", self.invariant), ("post", self.post)]:
            missing = f.vars - allowed_vars
            if missing:
                raise ValueError(f"змінні {sorted(missing)} у {f_name} відсутні у domains")
        if self.variant:
            missing = self.variant.vars - allowed_vars
            if missing:
                raise ValueError(f"змінні {sorted(missing)} у variant відсутні у domains")

    @staticmethod
    def from_json(path: str) -> "Spec":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return Spec(
            inputs=d["inputs"],
            pre=Formula(d["pre"]),
            invariant=Formula(d["invariant"]),
            post=Formula(d["post"]),
            domains={k: tuple(v) for k, v in d["domains"].items()},
            variant=Formula(d["variant"]) if d.get("variant") else None,
            ghosts=d.get("ghosts", {})
        )


@dataclass
class VCResult:
    name: str
    ok: bool
    checked: int
    counterexample: dict | None = None
    detail: str = ""
    formula: str = ""


def _flatten(s: A.ASTNode) -> list[A.ASTNode]:
    match s:
        case A.Program(body=b) | A.Block(body=b):
            return _flatten(b)
        case A.Seq(first=a, second=b):
            return _flatten(a) + _flatten(b)
    return [s]


def collect_variables(node: A.ASTNode) -> set[str]:
    vars_found: set[str] = set()
    match node:
        case A.Program(body=b) | A.Block(body=b):
            vars_found.update(collect_variables(b))
        case A.Seq(first=a, second=b):
            vars_found.update(collect_variables(a))
            vars_found.update(collect_variables(b))
        case A.Assign(var=v, expr=e):
            vars_found.add(v)
            vars_found.update(collect_variables(e))
        case A.If(cond=c, then=t, orelse=e):
            vars_found.update(collect_variables(c))
            vars_found.update(collect_variables(t))
            vars_found.update(collect_variables(e))
        case A.While(cond=c, body=b):
            vars_found.update(collect_variables(c))
            vars_found.update(collect_variables(b))
        case A.BinOp(left=l, right=r) | A.Logic(left=l, right=r) | A.Rel(left=l, right=r):
            vars_found.update(collect_variables(l))
            vars_found.update(collect_variables(r))
        case A.Not(operand=op):
            vars_found.update(collect_variables(op))
        case A.Var(name=n):
            vars_found.add(n)
        case _:
            pass
    return vars_found


def split_loop(program: A.Program):
    items = _flatten(program)
    loops = [i for i, s in enumerate(items) if isinstance(s, A.While)]
    if len(loops) != 1:
        raise ValueError(f"підтримується рівно один цикл while на верхньому рівні програми, знайдено: {len(loops)}")
    i = loops[0]
    return items[:i], items[i], items[i + 1:]


def _compose(stmts: list[A.ASTNode]) -> T.Term:
    terms = [build_term(s) for s in stmts]
    if not terms:
        return T.ID()
    out = terms[-1]
    for t in reversed(terms[:-1]):
        out = T.Comp(t, out)
    return out


def _states(domains: dict[str, tuple[int, int]]):
    names = sorted(domains)
    for vals in itertools.product(*(range(domains[n][0], domains[n][1] + 1) for n in names)):
        yield dict(zip(names, vals))


def verify(program: A.Program, spec: Spec) -> list[VCResult]:
    spec.validate()
    prog_vars = collect_variables(program)
    missing_vars = prog_vars - set(spec.domains.keys())
    if missing_vars:
        raise ValueError(f"змінні програми {sorted(missing_vars)} відсутні у domains специфікації")
    prefix, loop, suffix = split_loop(program)
    ev = Evaluator(max_steps=10_000)
    init_t, body_t, tail_t = _compose(prefix), build_term(loop.body), _compose(suffix)
    cond_t = build_bexp(loop.cond)
    inv, post, V = spec.invariant, spec.post, spec.variant

    vc1 = VCResult("VC1 база: P & init => Inv", True, 0)
    in_dom = {k: v for k, v in spec.domains.items() if k in spec.inputs}
    for inp in _states(in_dom):
        if not spec.pre(inp):
            continue
        st = {**inp, **{g: inp[src] for g, src in spec.ghosts.items()}}
        res = ev.run(init_t, st)
        vc1.checked += 1
        if res.status != "defined" or not inv(res.state):
            vc1.ok, vc1.counterexample = False, {"вхід": inp, "стан після ініціалізації": res.state}
            break

    vc2 = VCResult("VC2 крок: Inv & B => Inv після тіла", True, 0)
    vc3 = VCResult("VC3 вихід: Inv & not B => Q", True, 0)
    vc4 = VCResult("VC4 завершення: V>0 і V спадає", True, 0,
                   detail="" if V else "пропущено: variant не задано")
    vc1.formula = f"({spec.pre.src}) і {init_t} => ({inv.src})"
    vc2.formula = f"({inv.src}) і ({cond_t}) => ({inv.src}) після {body_t}"
    vc3.formula = f"({inv.src}) і не ({cond_t}) => ({post.src}) після {tail_t}"
    if V:
        vc4.formula = f"({inv.src}) і ({cond_t}) => ({V.src}) > 0 і ({V.src}) строго спадає після {body_t}"

    for st in _states(spec.domains):
        if not inv(st):
            continue
        if ev.value(cond_t, st):
            res = ev.run(body_t, st)
            vc2.checked += 1
            if vc2.ok and (res.status != "defined" or not inv(res.state)):
                vc2.ok, vc2.counterexample = False, {"до": st, "після тіла": res.state}
            if V and vc4.ok:
                vc4.checked += 1
                v_before = V(st)
                if not (v_before > 0 and res.status == "defined" and V(res.state) < v_before):
                    vc4.ok, vc4.counterexample = False, {"до": st, "після тіла": res.state}
        else:
            res = ev.run(tail_t, st)
            vc3.checked += 1
            if vc3.ok and (res.status != "defined" or not post(res.state)):
                vc3.ok, vc3.counterexample = False, {"стан на виході": st, "після суфікса": res.state}

    if vc1.checked == 0:
        vc1.ok = False
        vc1.detail = "помилка: 0 станів задовольнили передумову"
    if vc2.checked == 0:
        vc2.ok = False
        vc2.detail = "помилка: 0 станів задовольнили інваріант та умову циклу"
    if vc3.checked == 0:
        vc3.ok = False
        vc3.detail = "помилка: 0 станів задовольнили інваріант та вихід з циклу"
    if V and vc4.checked == 0:
        vc4.ok = False
        vc4.detail = "помилка: 0 станів для перевірки спадання варіанта"

    return [vc1, vc2, vc3, vc4]
