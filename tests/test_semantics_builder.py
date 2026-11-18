from sipl.parser import parse
from sipl.semantics.builder import build_term


def test_builder_variant5_formula():
    code = """begin
  R := 1;
  while N > 0 do
  begin
    R := R * N * 2;
    N := N - 1
  end
end"""
    rules = []
    t = build_term(parse(code), rules=rules)
    expected = "AS_R(1) * WH(S2(gr, N=>, 0), AS_R(S2(mult, S2(mult, R=>, N=>), 2)) * AS_N(S2(sub, N=>, 1)))"
    assert str(t) == expected
    assert "NS_Prog" in rules
    assert "NS_Stm_Seq" in rules
    assert "NS_Stm_As" in rules
    assert "NS_Stm_Wh" in rules
    assert "NS_Stm_BE" in rules


def test_builder_power_formula():
    code = """begin
  R := 1;
  while Y > 0 do
  begin
    R := R * X;
    Y := Y - 1
  end
end"""
    t = build_term(parse(code))
    expected = "AS_R(1) * WH(S2(gr, Y=>, 0), AS_R(S2(mult, R=>, X=>)) * AS_Y(S2(sub, Y=>, 1)))"
    assert str(t) == expected


def test_builder_if_and_skip():
    code = "begin if X = 0 then skip else Y := Y + 1 end"
    t = build_term(parse(code))
    expected = "IF(S2(eq, X=>, 0), ID, AS_Y(S2(add, Y=>, 1)))"
    assert str(t) == expected
