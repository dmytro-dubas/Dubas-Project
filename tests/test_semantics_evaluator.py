from sipl.parser import parse
from sipl.semantics.builder import build_term
from sipl.semantics.evaluator import Evaluator


def test_evaluator_variant5_n2():
    code = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N * 2;
    N := N - 1
  end
end"""
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {"N": 2})
    assert res.status == "defined"
    assert res.state == {"N": 0, "R": 8}
    assert len(res.trace) == 11
    assert any(s.rule == "AF_SEQ" for s in res.trace)


def test_evaluator_variant5_n1():
    code = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N * 2;
    N := N - 1
  end
end"""
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {"N": 1})
    assert res.status == "defined"
    assert res.state == {"N": 0, "R": 2}


def test_evaluator_infinite_loop_limit():
    code = "begin while true do skip end"
    ev = Evaluator(max_steps=50)
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "undefined"
    assert "перевищено ліміт 50 кроків" in res.reason


def test_evaluator_undefined_variable():
    code = "begin R := X + 1 end"
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "undefined"
    assert "не визначена" in res.reason


def test_evaluator_seq_trace():
    code = "begin X := 1; Y := 2 end"
    ev = Evaluator()
    res = ev.run(build_term(parse(code)), {})
    assert res.status == "defined"
    assert res.state == {"X": 1, "Y": 2}
    assert len(res.trace) == 3
    assert [s.rule for s in res.trace] == ["AF_SEQ", "AF_AS", "AF_AS"]
    assert res.trace[0].rule == "AF_SEQ"
    assert res.trace[0].detail == "AS_X(1) * AS_Y(2)"
    assert res.trace[0].before == {}
    assert res.trace[0].after == {}


test_evaluator_af_seq = test_evaluator_seq_trace
