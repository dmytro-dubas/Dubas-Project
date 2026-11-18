from __future__ import annotations
from .. import ast as A
from . import terms as T

AOPS = {"+": "add", "-": "sub", "*": "mult"}
ROPS = {">": "gr", "<": "ls", ">=": "ge", "<=": "le", "=": "eq"}


def build_aexp(e: A.ASTNode) -> T.Term:
    match e:
        case A.Num(value=v):                  return T.Const(v)
        case A.Var(name=n):                   return T.Den(n)
        case A.BinOp(op=o, left=l, right=r):  return T.S2(AOPS[o], build_aexp(l), build_aexp(r))
    raise TypeError(f"не арифметичний вираз: {e!r}")


def build_bexp(e: A.ASTNode) -> T.Term:
    match e:
        case A.BoolConst(value=v):            return T.Const(v)
        case A.Rel(op=o, left=l, right=r):    return T.S2(ROPS[o], build_aexp(l), build_aexp(r))
        case A.Not(operand=x):                return T.S1("neg", build_bexp(x))
        case A.Logic(op=o, left=l, right=r):  return T.S2(o, build_bexp(l), build_bexp(r))
    raise TypeError(f"не булів вираз: {e!r}")


def build_term(s: A.ASTNode, rules: list[str] | None = None) -> T.Term:
    def note(r: str):
        if rules is not None:
            rules.append(r)

    match s:
        case A.Program(body=b):           note("NS_Prog");   return build_term(b, rules)
        case A.Assign(var=v, expr=e):     note("NS_Stm_As"); return T.AS(v, build_aexp(e))
        case A.Seq(first=a, second=b):
            note("NS_Stm_Seq");           return T.Comp(build_term(a, rules), build_term(b, rules))
        case A.If(cond=c, then=t, orelse=e):
            note("NS_Stm_If");            return T.IF(build_bexp(c), build_term(t, rules), build_term(e, rules))
        case A.While(cond=c, body=b):
            note("NS_Stm_Wh");            return T.WH(build_bexp(c), build_term(b, rules))
        case A.Block(body=b):             note("NS_Stm_BE"); return build_term(b, rules)
        case A.Skip():                    note("NS_Stm_Sk"); return T.ID()
    raise TypeError(f"не оператор: {s!r}")
