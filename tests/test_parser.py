from pathlib import Path
import pytest
from sipl.parser import parse, parse_tree, SIPLSyntaxError, _load_grammar, _GRAMMAR
from sipl import ast as A


def test_parse_simple_assign():
    p = parse("begin X := 5 end")
    assert isinstance(p, A.Program)
    assert isinstance(p.body, A.Assign)
    assert p.body.var == "X"
    assert isinstance(p.body.expr, A.Num)
    assert p.body.expr.value == 5
    assert p.span.start_line == 1


def test_parse_seq():
    p = parse("begin X := 1; Y := 2 end")
    assert isinstance(p.body, A.Seq)
    assert isinstance(p.body.first, A.Assign)
    assert isinstance(p.body.second, A.Assign)


def test_parse_if_else():
    p = parse("begin if X > 0 then Y := 1 else Y := 0 end")
    assert isinstance(p.body, A.If)
    assert isinstance(p.body.cond, A.Rel)
    assert p.body.cond.op == ">"


def test_parse_while():
    p = parse("begin while N > 0 do N := N - 1 end")
    assert isinstance(p.body, A.While)
    assert isinstance(p.body.cond, A.Rel)


def test_parse_block():
    p = parse("begin begin skip end end")
    assert isinstance(p.body, A.Block)
    assert isinstance(p.body.body, A.Skip)


def test_parse_skip():
    p = parse("begin skip end")
    assert isinstance(p.body, A.Skip)


def test_parse_arithmetic_precedence():
    p = parse("begin R := 1 + 2 * 3 end")
    expr = p.body.expr
    assert isinstance(expr, A.BinOp)
    assert expr.op == "+"
    assert isinstance(expr.right, A.BinOp)
    assert expr.right.op == "*"


def test_parse_boolean_logic():
    p = parse("begin if not (X > 0 and Y <= 10) then skip else skip end")
    cond = p.body.cond
    assert isinstance(cond, A.Not)
    assert isinstance(cond.operand, A.Logic)
    assert cond.operand.op == "and"


def test_parse_variant5():
    code = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N * 2;
    N := N - 1
  end
end"""
    p = parse(code)
    assert isinstance(p.body, A.Seq)
    assert p.body.first.var == "R"
    assert isinstance(p.body.second, A.While)


def test_syntax_missing_end():
    with pytest.raises(SIPLSyntaxError) as exc:
        parse("begin X := 1")
    assert "забули 'end'" in exc.value.msg or "неочікуваний кінець" in exc.value.msg


def test_syntax_missing_begin():
    with pytest.raises(SIPLSyntaxError):
        parse("X := 1 end")


def test_syntax_missing_assign_rhs():
    with pytest.raises(SIPLSyntaxError):
        parse("begin X := end")


def test_syntax_invalid_char():
    with pytest.raises(SIPLSyntaxError) as exc:
        parse("begin X := @1 end")
    assert "@" in exc.value.render()


def test_syntax_double_semicolon():
    with pytest.raises(SIPLSyntaxError):
        parse("begin X := 1;; Y := 2 end")


def test_syntax_missing_else():
    with pytest.raises(SIPLSyntaxError):
        parse("begin if X > 0 then Y := 1 end")


def test_syntax_missing_do():
    with pytest.raises(SIPLSyntaxError):
        parse("begin while X > 0 Y := 1 end")


def test_syntax_unclosed_paren():
    with pytest.raises(SIPLSyntaxError):
        parse("begin X := (1 + 2 end")


def test_syntax_empty_program():
    with pytest.raises(SIPLSyntaxError):
        parse("")


def test_syntax_multiple_stmts_in_while_without_begin_end():
    with pytest.raises(SIPLSyntaxError):
        parse("begin while X > 0 do R := 1 N := 2 end")


def test_grammar_files_consistency():
    repo_root = Path(__file__).resolve().parent.parent
    grammar_repo = repo_root / "grammar" / "sipl.lark"
    grammar_pkg = repo_root / "src" / "sipl" / "sipl.lark"
    if grammar_repo.exists() and grammar_pkg.exists():
        text_repo = grammar_repo.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        text_pkg = grammar_pkg.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
        assert text_repo == text_pkg
        assert _GRAMMAR.replace("\r\n", "\n").strip() == text_repo


def test_load_grammar_callable():
    grammar = _load_grammar()
    assert 'start: "begin" stm "end"' in grammar
    assert grammar == _GRAMMAR


def test_parse_deep_program_500_statements():
    code = "begin " + "; ".join(f"X := {i}" for i in range(500)) + " end"
    p = parse(code)
    assert isinstance(p, A.Program)


def test_parse_tree_keep_tokens_flag():
    cst = parse_tree("begin X := 1 end", keep_tokens=True)
    tokens = [str(c.value) for c in cst.children if hasattr(c, "value")]
    assert "begin" in tokens
    assert "end" in tokens


