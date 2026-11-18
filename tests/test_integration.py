import json
import math
from pathlib import Path
import xml.dom.minidom as dom
import pytest

from sipl.ast import (
    Assign, BinOp, Block, BoolConst, If, Logic,
    Not, Num, Program, Rel, Seq, Skip, Var, While
)
from sipl.cli import main, parse_state
from sipl.parser import parse, parse_file, parse_tree, SIPLSyntaxError
from sipl.semantics.builder import build_term
from sipl.semantics.evaluator import Evaluator, fmt_state
from sipl.semantics.verifier import FUNCS, Formula, Spec, split_loop, verify
from sipl.visualization import tree as vis_tree

EXAMPLES = Path(__file__).parent.parent / "examples"

FACTORIAL_SRC = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N;
    N := N - 1
  end
end"""

POWER_SRC = """begin
  R := 1;
  while Y > 0 do
  begin
    R := R * X;
    Y := Y - 1
  end
end"""

VARIANT5_SRC = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N * 2;
    N := N - 1
  end
end"""

GCD_SRC = """begin
  while A > B or B > A do
  begin
    if A > B then
      A := A - B
    else
      B := B - A
  end
end"""

FIBONACCI_SRC = """begin
  A := 0;
  B := 1;
  while N > 0 do
  begin
    T := A + B;
    A := B;
    B := T;
    N := N - 1
  end
end"""

SUM_N_SRC = """begin
  S := 0;
  while N > 0 do
  begin
    S := S + N;
    N := N - 1
  end
end"""


def _ensure_funcs():
    FUNCS["gcd"] = math.gcd
    if "fib" not in FUNCS:
        def _fib(n: int) -> int:
            if n <= 0:
                return 0
            if n == 1:
                return 1
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a
        FUNCS["fib"] = _fib


def test_cli_parse_command(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    ret = main(["parse", str(sipl_file)])
    out, err = capsys.readouterr()
    assert ret == 0
    assert "[OK] Синтаксично коректно" in out
    assert "Span програми:" in out
    assert err == ""


def test_cli_tree_formats(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    for fmt in ["text", "json", "dot", "svg"]:
        ret = main(["tree", str(sipl_file), "--format", fmt])
        out, err = capsys.readouterr()
        assert ret == 0
        assert err == ""
        if fmt == "text":
            assert "program" in out
            assert "1:1" in out
        elif fmt == "json":
            data = json.loads(out)
            assert data["kind"] == "nonterminal"
            assert data["name"] == "program"
        elif fmt == "dot":
            assert out.startswith("digraph ParseTree {")
            assert "->" in out
        elif fmt == "svg":
            doc = dom.parseString(out)
            assert doc.documentElement.tagName == "svg"


def test_cli_tree_out_file(tmp_path, capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    out_svg = tmp_path / "tree.svg"
    ret = main(["tree", str(sipl_file), "--format", "svg", "--out", str(out_svg)])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "[OK] Дерево виводу успішно збережено у" in out
    assert out_svg.exists()
    doc = dom.parseString(out_svg.read_text(encoding="utf-8"))
    assert doc.documentElement.tagName == "svg"


def test_cli_term_command(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    ret = main(["term", str(sipl_file)])
    out, err = capsys.readouterr()
    assert ret == 0
    assert err == ""
    assert "AS_R(1)" in out
    assert "WH(S2(gr, N=>, 0)" in out


def test_cli_eval_command_with_trace(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    ret = main(["eval", str(sipl_file), "--state", "N=2", "--trace"])
    out, err = capsys.readouterr()
    assert ret == 0
    assert err == ""
    assert "AF_SEQ" in out
    assert "AF_AS" in out
    assert "AF_WH_TRUE" in out
    assert "AF_WH_FALSE" in out
    assert "[N -> 0, R -> 8]" in out


def test_cli_verify_command_success(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    spec_file = EXAMPLES / "variant5_double_fact.spec.json"
    ret = main(["verify", str(sipl_file), "--spec", str(spec_file)])
    out, err = capsys.readouterr()
    assert ret == 0
    assert err == ""
    assert "[OK] VC1" in out
    assert "[OK] VC2" in out
    assert "[OK] VC3" in out
    assert "[OK] VC4" in out


def test_cli_verify_command_failure(capsys):
    sipl_file = EXAMPLES / "variant5_double_fact.sipl"
    spec_file = EXAMPLES / "variant5_incorrect.spec.json"
    ret = main(["verify", str(sipl_file), "--spec", str(spec_file)])
    out, _ = capsys.readouterr()
    assert ret == 1
    assert "[FAIL] VC2" in out
    assert "контрприклад:" in out


def test_programmatic_ast_nodes():
    code = """begin
  skip;
  X := 10;
  if X > 5 and not (X = 0) or X <= 1 then
    begin
      Y := X + 2 * 3 - 1
    end
  else
    skip;
  while Y >= 0 do
    Y := Y - 1
end"""
    prog = parse(code)
    assert isinstance(prog, Program)
    assert isinstance(prog.body, Seq)
    assert prog.span is not None

    assign = parse("begin X := 42 end").body
    assert isinstance(assign, Assign)
    assert assign.var == "X"
    assert isinstance(assign.expr, Num)
    assert assign.expr.value == 42

    cond = parse("begin if not (A = B) then skip else skip end").body
    assert isinstance(cond, If)
    assert isinstance(cond.cond, Not)
    assert isinstance(cond.cond.operand, Rel)
    assert cond.cond.operand.op == "="
    assert isinstance(cond.cond.operand.left, Var)
    assert isinstance(cond.cond.operand.right, Var)

    loop = parse("begin while A < B and C <= D or E > F do skip end").body
    assert isinstance(loop, While)
    assert isinstance(loop.cond, Logic)
    assert isinstance(loop.body, Skip)

    arith = parse("begin X := (A + B) * (C - D) end").body
    assert isinstance(arith, Assign)
    assert isinstance(arith.expr, BinOp)
    assert arith.expr.op == "*"
    assert isinstance(arith.expr.left, BinOp)
    assert arith.expr.left.op == "+"
    assert isinstance(arith.expr.right, BinOp)
    assert arith.expr.right.op == "-"


def test_programmatic_span_coordinates():
    code = "begin\n  X := 1;\n  Y := 2\nend"
    prog = parse(code)
    assert prog.span.start_line == 1
    assert prog.span.start_col == 1
    assert str(prog.span) == f"{prog.span.start_line}:{prog.span.start_col}-{prog.span.end_line}:{prog.span.end_col}"


def test_eval_trace_full_rules():
    code = """begin
  X := 1;
  if X > 0 then
    Y := 10
  else
    Y := 20;
  while X > 0 do
    X := X - 1
end"""
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "defined"
    assert res.state == {"X": 0, "Y": 10}
    rules = [s.rule for s in res.trace]
    assert "AF_SEQ" in rules
    assert "AF_AS" in rules
    assert "AF_IF_TRUE" in rules
    assert "AF_WH_TRUE" in rules
    assert "AF_WH_FALSE" in rules


def test_verify_all_benchmarks_pass():
    benchmarks = ["factorial", "power", "sum_n", "variant5_double_fact"]
    for name in benchmarks:
        prog = parse_file(str(EXAMPLES / f"{name}.sipl"))
        spec = Spec.from_json(str(EXAMPLES / f"{name}.spec.json"))
        results = verify(prog, spec)
        assert len(results) == 4
        assert all(r.ok for r in results)
        assert all(r.checked > 0 for r in results)


def test_cli_file_not_found(capsys):
    commands = [
        ["parse", "missing.sipl"],
        ["tree", "missing.sipl"],
        ["term", "missing.sipl"],
        ["eval", "missing.sipl"],
        ["verify", "missing.sipl", "--spec", str(EXAMPLES / "factorial.spec.json")],
    ]
    for cmd in commands:
        ret = main(cmd)
        _, err = capsys.readouterr()
        assert ret == 1
        assert "Помилка: файл 'missing.sipl' не знайдено" in err


def test_cli_missing_spec_file(capsys):
    sipl_file = EXAMPLES / "factorial.sipl"
    ret = main(["verify", str(sipl_file), "--spec", "missing_spec.json"])
    _, err = capsys.readouterr()
    assert ret == 1
    assert "Помилка: файл 'missing_spec.json' не знайдено" in err


def test_syntax_error_caret_alignment():
    code = "begin\n  R := 1\n  while N > 0 do\n    skip\nend"
    with pytest.raises(SIPLSyntaxError) as exc_info:
        parse(code)
    err = exc_info.value
    assert err.line == 3
    assert err.col == 3
    rendered = err.render()
    assert "Синтаксична помилка (3:3):" in rendered
    assert "while N > 0 do" in rendered
    assert "^" in rendered
    lines = rendered.splitlines()
    assert lines[-1].strip() == "^"
    assert lines[-1] == f"  {' ' * (err.col - 1)}^"


def test_cli_syntax_error_exit_code(capsys):
    sipl_file = EXAMPLES / "invalid_syntax.sipl"
    ret = main(["parse", str(sipl_file)])
    _, err = capsys.readouterr()
    assert ret == 2
    assert "Синтаксична помилка" in err
    assert "^" in err


def test_parser_empty_and_whitespace():
    for src in ["", "   ", "\n\t  \n"]:
        with pytest.raises(SIPLSyntaxError) as exc_info:
            parse(src)
        assert exc_info.value.line == 1
        assert exc_info.value.col == 1


def test_parser_single_tokens():
    for token in ["begin", "skip", "end", "42", "X"]:
        with pytest.raises(SIPLSyntaxError):
            parse(token)


def test_parser_extreme_nesting():
    expr = "1"
    for _ in range(50):
        expr = f"({expr} + 1)"
    code_expr = f"begin X := {expr} end"
    prog1 = parse(code_expr)
    assert isinstance(prog1, Program)

    code_block = "skip"
    for _ in range(50):
        code_block = f"begin {code_block} end"
    prog2 = parse(code_block)
    assert isinstance(prog2, Program)

    cst = parse_tree(code_block)
    txt = vis_tree.to_text(cst)
    assert "program" in txt
    raw_json = vis_tree.to_json(cst)
    assert json.loads(raw_json)["name"] == "program"


def test_visualization_svg_relational_operators():
    code = "begin while X < 5 and Y <= 10 and Z > 0 and W >= 1 and A = 0 do skip end"
    cst = parse_tree(code)
    svg = vis_tree.to_svg(cst)
    assert "&lt;" in svg
    assert "&gt;" in svg
    doc = dom.parseString(svg)
    assert doc.documentElement.tagName == "svg"
    texts = [n.firstChild.nodeValue for n in doc.getElementsByTagName("text") if n.firstChild]
    assert "'<'" in texts
    assert "'<='" in texts
    assert "'>'" in texts
    assert "'>='" in texts
    assert "'='" in texts


def test_spec_empty_domains_rejected():
    with pytest.raises(ValueError, match="не можуть бути порожніми"):
        Spec(
            inputs=["N"],
            pre=Formula("N >= 0"),
            invariant=Formula("N == N"),
            post=Formula("N == N"),
            domains={}
        )


def test_spec_inverted_range_rejected():
    with pytest.raises(ValueError, match="некоректний діапазон"):
        Spec(
            inputs=["N"],
            pre=Formula("N >= 0"),
            invariant=Formula("N == N"),
            post=Formula("N == N"),
            domains={"N": (10, 2)}
        )


def test_spec_missing_variables_rejected():
    with pytest.raises(ValueError, match="відсутні у domains"):
        Spec(
            inputs=["N"],
            pre=Formula("N >= 0"),
            invariant=Formula("R == N"),
            post=Formula("R == N"),
            domains={"N": (0, 5)}
        )


def test_vacuous_truth_precondition_rejected(capsys, tmp_path):
    spec_data = {
        "inputs": ["N"],
        "pre": "N > 100",
        "invariant": "R * fact(N) == fact(N0)",
        "post": "R == fact(N0)",
        "variant": "N",
        "domains": {"N": [0, 5], "N0": [0, 5], "R": [1, 120]},
        "ghosts": {"N0": "N"}
    }
    spec_path = tmp_path / "vacuous.json"
    spec_path.write_text(json.dumps(spec_data), encoding="utf-8")
    sipl_file = EXAMPLES / "factorial.sipl"
    ret = main(["verify", str(sipl_file), "--spec", str(spec_path)])
    out, _ = capsys.readouterr()
    assert ret == 1
    assert "[FAIL] VC1" in out
    assert "0 станів задовольнили передумову" in out


def test_vacuous_truth_loop_condition_rejected():
    prog = parse("begin R := 1; while N > 10 do N := N - 1 end")
    spec = Spec(
        inputs=["N"],
        pre=Formula("N == 5"),
        invariant=Formula("N <= 5"),
        post=Formula("N <= 5"),
        domains={"N": (0, 5), "R": (1, 1)}
    )
    results = verify(prog, spec)
    vc2 = next(r for r in results if "VC2" in r.name)
    assert vc2.checked == 0
    assert vc2.ok is False
    assert "0 станів задовольнили" in vc2.detail


def test_eval_while_zero_iterations():
    code = "begin while N > 10 do N := N - 1 end"
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {"N": 5})
    assert res.status == "defined"
    assert res.state == {"N": 5}
    assert len(res.trace) == 1
    assert res.trace[0].rule == "AF_WH_FALSE"
    assert res.trace[0].before == {"N": 5}
    assert res.trace[0].after == {"N": 5}


def test_eval_max_steps_exceeded():
    code = "begin while true do X := X + 1 end"
    ev = Evaluator(max_steps=25)
    res = ev.run(build_term(parse(code)), {"X": 0})
    assert res.status == "undefined"
    assert res.state is None
    assert "перевищено ліміт 25 кроків" in res.reason
    assert len(res.trace) == 25


def test_eval_undefined_variable_error():
    code = "begin Y := X + 1 end"
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "undefined"
    assert "не визначена у стані" in res.reason


def test_eval_negative_numbers_arithmetic():
    code = "begin X := 0 - 15; Y := X + 5; Z := X * 2 end"
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "defined"
    assert res.state == {"X": -15, "Y": -10, "Z": -30}


def test_verifier_negative_domain_bounds():
    spec = Spec(
        inputs=["N"],
        pre=Formula("N <= -2"),
        invariant=Formula("N <= 0"),
        post=Formula("N <= 0"),
        domains={"N": (-5, -1)}
    )
    assert spec.domains["N"] == (-5, -1)


def test_verifier_single_point_domain():
    prog = parse("begin R := 1; while N > 0 do begin R := R * 2; N := N - 1 end end")
    spec = Spec(
        inputs=["N"],
        pre=Formula("N == 1"),
        invariant=Formula("R * pow(2, N) == 2"),
        post=Formula("R == 2"),
        variant=Formula("N"),
        domains={"N": (0, 1), "R": (1, 2)}
    )
    results = verify(prog, spec)
    assert all(r.ok for r in results)
    assert all(r.checked == 1 for r in results)


def test_verifier_invalid_loop_structure():
    with pytest.raises(ValueError, match="підтримується рівно один цикл while"):
        split_loop(parse("begin X := 1 end"))

    with pytest.raises(ValueError, match="підтримується рівно один цикл while"):
        split_loop(parse("begin while X > 0 do X := X - 1; while Y > 0 do Y := Y - 1 end"))


def test_cli_parse_state_edge_cases():
    assert parse_state("") == {}
    assert parse_state("  N = -5 ,  X = 10 ") == {"N": -5, "X": 10}
    assert parse_state("N=2,") == {"N": 2}

    with pytest.raises(ValueError, match="невірний формат"):
        parse_state("N")

    with pytest.raises(ValueError, match="має бути цілим числом"):
        parse_state("N=abc")


def test_cli_argparse_validations():
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        main(["unknown_cmd"])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        main(["tree", str(EXAMPLES / "factorial.sipl"), "--format", "pdf"])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        main(["verify", str(EXAMPLES / "factorial.sipl")])
    assert exc_info.value.code == 2

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_pipeline_full_cycle(tmp_path):
    cst = parse_tree(VARIANT5_SRC)
    assert cst is not None

    svg = vis_tree.to_svg(cst)
    doc = dom.parseString(svg)
    assert doc.documentElement.tagName == "svg"

    raw_json = vis_tree.to_json(cst)
    data = json.loads(raw_json)
    assert data["kind"] == "nonterminal"
    assert data["name"] == "program"

    prog = parse(VARIANT5_SRC)
    assert prog.span is not None

    rules = []
    term = build_term(prog, rules)
    assert "NS_Prog" in rules
    assert "NS_Stm_Seq" in rules
    assert "NS_Stm_Wh" in rules

    ev = Evaluator()
    res = ev.run(term, {"N": 2})
    assert res.status == "defined"
    assert res.state == {"N": 0, "R": 8}
    assert len(res.trace) == 11
    assert any(s.rule == "AF_SEQ" for s in res.trace)

    spec = Spec.from_json(str(EXAMPLES / "variant5_double_fact.spec.json"))
    v_results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in v_results)

    src_file = tmp_path / "variant5.sipl"
    src_file.write_text(VARIANT5_SRC, encoding="utf-8")
    assert main(["parse", str(src_file)]) == 0
    assert main(["term", str(src_file)]) == 0
    assert main(["eval", str(src_file), "--state", "N=2"]) == 0


def test_cli_flag_matrix(tmp_path, capsys):
    src_file = tmp_path / "fact.sipl"
    src_file.write_text(FACTORIAL_SRC, encoding="utf-8")

    for fmt in ["text", "json", "dot", "svg"]:
        out_file = tmp_path / f"tree.{fmt}"
        ret = main(["tree", str(src_file), "--format", fmt, "--out", str(out_file)])
        assert ret == 0
        assert out_file.exists()
        assert out_file.stat().st_size > 0

    assert main(["eval", str(src_file), "--state", "N=3"]) == 0
    out, _ = capsys.readouterr()
    assert "[N -> 0, R -> 6]" in out

    assert main(["eval", str(src_file), "--state", "N=2", "--trace"]) == 0
    out, _ = capsys.readouterr()
    assert "AF_SEQ" in out
    assert "AF_WH_TRUE" in out

    assert main(["eval", str(src_file), "--state", "N=5", "--max-steps", "5"]) == 1
    out, _ = capsys.readouterr()
    assert "перевищено ліміт 5 кроків" in out


def test_bidirectional_state_and_terms():
    st = parse_state("N=5, R=120, X=2")
    assert st == {"N": 5, "R": 120, "X": 2}
    formatted = fmt_state(st)
    assert formatted == "[N -> 5, R -> 120, X -> 2]"

    prog = parse("begin R := 1; N := N - 1 end")
    term = build_term(prog)
    assert str(term) == "AS_R(1) * AS_N(S2(sub, N=>, 1))"


def test_operator_precedence_and_escaping():
    code = "begin while (X + 2 * Y <= 10) and not (Z >= 5) do X := X + 1 end"
    cst = parse_tree(code)
    svg = vis_tree.to_svg(cst)
    doc = dom.parseString(svg)
    assert doc.documentElement.tagName == "svg"

    prog = parse(code)
    term = build_term(prog)
    assert "S2(mult, 2, Y=>)" in str(term)


def test_error_propagation_across_stages(tmp_path):
    bad_syntax = tmp_path / "bad.sipl"
    bad_syntax.write_text("begin X := 1 Y := 2 end", encoding="utf-8")
    assert main(["parse", str(bad_syntax)]) == 2
    assert main(["eval", str(bad_syntax)]) == 2

    undef_file = tmp_path / "undef.sipl"
    undef_file.write_text("begin R := X + 1 end", encoding="utf-8")
    assert main(["eval", str(undef_file), "--state", ""]) == 1


def test_workload_factorial():
    _ensure_funcs()
    prog = parse(FACTORIAL_SRC)
    term = build_term(prog)
    ev = Evaluator()

    for n in [0, 1, 3, 5]:
        res = ev.run(term, {"N": n})
        assert res.status == "defined"
        assert res.state["R"] == math.factorial(n)
        assert len(res.trace) == 3 + 4 * n

    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("R * fact(N) == fact(N0)"),
        post=Formula("R == fact(N0)"),
        variant=Formula("N"),
        domains={"N": (0, 5), "N0": (0, 5), "R": (1, 120)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)

    bad_spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("R * fact(N) == fact(N0) + 1"),
        post=Formula("R == fact(N0)"),
        variant=Formula("N"),
        domains={"N": (0, 5), "N0": (0, 5), "R": (1, 120)},
        ghosts={"N0": "N"}
    )
    bad_results = verify(prog, bad_spec)
    assert not all(r.ok for r in bad_results)


def test_workload_power():
    _ensure_funcs()
    prog = parse(POWER_SRC)
    term = build_term(prog)
    ev = Evaluator()

    for x, y in [(2, 0), (2, 8), (3, 4), (5, 3)]:
        res = ev.run(term, {"X": x, "Y": y})
        assert res.status == "defined"
        assert res.state["R"] == x ** y
        assert len(res.trace) == 3 + 4 * y

    spec = Spec(
        inputs=["X", "Y"],
        pre=Formula("Y >= 0 and X >= 1"),
        invariant=Formula("R * pow(X, Y) == pow(X, Y0)"),
        post=Formula("R == pow(X, Y0)"),
        variant=Formula("Y"),
        domains={"X": (2, 3), "Y": (0, 4), "Y0": (0, 4), "R": (1, 81)},
        ghosts={"Y0": "Y"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)


def test_workload_variant5_double_factorial():
    _ensure_funcs()
    prog = parse(VARIANT5_SRC)
    term = build_term(prog)
    ev = Evaluator()

    expected_vals = {1: 2, 2: 8, 3: 48, 4: 384}
    for n, expected in expected_vals.items():
        res = ev.run(term, {"N": n})
        assert res.status == "defined"
        assert res.state["R"] == expected
        assert len(res.trace) == 3 + 4 * n

    res2 = ev.run(term, {"N": 2})
    assert len(res2.trace) == 11
    assert [s.rule for s in res2.trace].count("AF_SEQ") == 3

    spec = Spec(
        inputs=["N"],
        pre=Formula("N > 0"),
        invariant=Formula("R * dfact(2 * N) == dfact(2 * N0)"),
        post=Formula("R == dfact(2 * N0)"),
        variant=Formula("N"),
        domains={"N": (0, 4), "N0": (1, 4), "R": (1, 384)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)


def test_workload_gcd_euclidean():
    _ensure_funcs()
    prog = parse(GCD_SRC)
    term = build_term(prog)
    ev = Evaluator()

    pairs = [(48, 18), (17, 13), (54, 24), (100, 25), (7, 7)]
    for a, b in pairs:
        res = ev.run(term, {"A": a, "B": b})
        assert res.status == "defined"
        expected = math.gcd(a, b)
        assert res.state["A"] == expected
        assert res.state["B"] == expected

    res_trace = ev.run(term, {"A": 10, "B": 4})
    rules = [s.rule for s in res_trace.trace]
    assert "AF_IF_TRUE" in rules
    assert "AF_IF_FALSE" in rules

    spec = Spec(
        inputs=["A", "B"],
        pre=Formula("A > 0 and B > 0"),
        invariant=Formula("A > 0 and B > 0 and gcd(A, B) == gcd(A0, B0)"),
        post=Formula("A == B and A == gcd(A0, B0)"),
        variant=Formula("A + B"),
        domains={"A": (1, 5), "B": (1, 5), "A0": (1, 5), "B0": (1, 5)},
        ghosts={"A0": "A", "B0": "B"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)

    bad_spec = Spec(
        inputs=["A", "B"],
        pre=Formula("A > 0 and B > 0"),
        invariant=Formula("A == B"),
        post=Formula("A == B and A == gcd(A0, B0)"),
        variant=Formula("A + B"),
        domains={"A": (1, 5), "B": (1, 5), "A0": (1, 5), "B0": (1, 5)},
        ghosts={"A0": "A", "B0": "B"}
    )
    bad_results = verify(prog, bad_spec)
    assert not all(r.ok for r in bad_results)


def test_workload_fibonacci():
    _ensure_funcs()
    prog = parse(FIBONACCI_SRC)
    term = build_term(prog)
    ev = Evaluator()

    for n in [0, 1, 2, 5, 8]:
        res = ev.run(term, {"N": n})
        assert res.status == "defined"
        assert res.state["A"] == FUNCS["fib"](n)
        assert len(res.trace) == 5 + 8 * n

    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("0 <= N and N <= N0 and A == fib(N0 - N) and B == fib(N0 - N + 1)"),
        post=Formula("A == fib(N0)"),
        variant=Formula("N"),
        domains={"N": (0, 4), "N0": (0, 4), "A": (0, 5), "B": (0, 8), "T": (0, 8)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)


def test_workload_sum_natural_numbers():
    _ensure_funcs()
    prog = parse(SUM_N_SRC)
    term = build_term(prog)
    ev = Evaluator()

    for n in [0, 1, 5, 10, 20]:
        res = ev.run(term, {"N": n})
        assert res.status == "defined"
        assert res.state["S"] == n * (n + 1) // 2
        assert len(res.trace) == 3 + 4 * n

    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("2 * S + N * (N + 1) == N0 * (N0 + 1)"),
        post=Formula("2 * S == N0 * (N0 + 1)"),
        variant=Formula("N"),
        domains={"N": (0, 5), "N0": (0, 5), "S": (0, 15)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    assert all(r.ok and r.checked > 0 for r in results)
