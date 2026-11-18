import pytest
from pathlib import Path
from sipl.parser import parse_file, parse
from sipl.semantics.verifier import Formula, Spec, verify

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_verifier_variant5_valid():
    prog = parse_file(str(EXAMPLES / "variant5_double_fact.sipl"))
    spec = Spec.from_json(str(EXAMPLES / "variant5_double_fact.spec.json"))
    results = verify(prog, spec)
    assert len(results) == 4
    assert all(r.ok for r in results)


def test_verifier_variant5_incorrect_invariant():
    prog = parse_file(str(EXAMPLES / "variant5_double_fact.sipl"))
    spec = Spec.from_json(str(EXAMPLES / "variant5_incorrect.spec.json"))
    results = verify(prog, spec)
    vc_by_name = {r.name.split()[0]: r for r in results}
    assert vc_by_name["VC1"].ok is True
    assert vc_by_name["VC2"].ok is False
    assert vc_by_name["VC2"].counterexample is not None


def test_verifier_factorial():
    prog = parse_file(str(EXAMPLES / "factorial.sipl"))
    spec = Spec.from_json(str(EXAMPLES / "factorial.spec.json"))
    results = verify(prog, spec)
    assert all(r.ok for r in results)


def test_verifier_power():
    prog = parse_file(str(EXAMPLES / "power.sipl"))
    spec = Spec.from_json(str(EXAMPLES / "power.spec.json"))
    results = verify(prog, spec)
    assert all(r.ok for r in results)


def test_verifier_sum_n():
    prog = parse_file(str(EXAMPLES / "sum_n.sipl"))
    spec = Spec.from_json(str(EXAMPLES / "sum_n.spec.json"))
    results = verify(prog, spec)
    assert all(r.ok for r in results)


def test_formula_vars_extraction():
    f1 = Formula("R * dfact(2 * N) == dfact(2 * N0)")
    assert f1.vars == {"R", "N", "N0"}
    f2 = Formula("pow(X, Y) >= 1")
    assert f2.vars == {"X", "Y"}
    f3 = Formula("True")
    assert f3.vars == set()


def test_spec_validate_empty_domains():
    with pytest.raises(ValueError, match="області значень.*порожніми"):
        Spec(
            inputs=["N"],
            pre=Formula("N > 0"),
            invariant=Formula("R == N"),
            post=Formula("R == N"),
            domains={}
        )


def test_spec_validate_missing_input():
    with pytest.raises(ValueError, match="вхідна змінна 'M' відсутня"):
        Spec(
            inputs=["N", "M"],
            pre=Formula("N > 0"),
            invariant=Formula("R == N"),
            post=Formula("R == N"),
            domains={"N": (0, 4), "R": (1, 10)}
        )


def test_spec_validate_missing_invariant_var():
    with pytest.raises(ValueError, match="змінні .* у invariant відсутні"):
        Spec(
            inputs=["N"],
            pre=Formula("N > 0"),
            invariant=Formula("R * dfact(2 * N) == dfact(2 * N0)"),
            post=Formula("R == N"),
            domains={"N": (0, 4), "R": (1, 10)}
        )


def test_spec_validate_invalid_range_min_greater_max():
    with pytest.raises(ValueError, match="некоректний діапазон.*N"):
        Spec(
            inputs=["N"],
            pre=Formula("N > 0"),
            invariant=Formula("R == N"),
            post=Formula("R == N"),
            domains={"N": (5, 2), "R": (1, 10)}
        )


def test_verifier_vacuous_precondition_fails():
    prog = parse_file(str(EXAMPLES / "variant5_double_fact.sipl"))
    spec = Spec(
        inputs=["N"],
        pre=Formula("N > 100"),
        invariant=Formula("R * dfact(2 * N) == dfact(2 * N0)"),
        post=Formula("R == dfact(2 * N0)"),
        variant=Formula("N"),
        domains={"N": (0, 4), "N0": (1, 4), "R": (1, 384)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    vc1 = next(r for r in results if r.name.startswith("VC1"))
    assert vc1.checked == 0
    assert vc1.ok is False
    assert "0 станів задовольнили передумову" in vc1.detail
    assert not all(r.ok for r in results)


def test_verifier_vacuous_loop_fails():
    prog = parse_file(str(EXAMPLES / "variant5_double_fact.sipl"))
    spec = Spec(
        inputs=["N"],
        pre=Formula("N == 0"),
        invariant=Formula("N == 0 and R == 1"),
        post=Formula("R == 1"),
        variant=Formula("N"),
        domains={"N": (0, 4), "N0": (0, 4), "R": (1, 384)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    vc2 = next(r for r in results if r.name.startswith("VC2"))
    assert vc2.checked == 0
    assert vc2.ok is False
    assert "0 станів задовольнили інваріант та умову циклу" in vc2.detail
    assert not all(r.ok for r in results)


def test_verifier_vacuous_exit_fails():
    prog = parse_file(str(EXAMPLES / "variant5_double_fact.sipl"))
    spec = Spec(
        inputs=["N"],
        pre=Formula("N > 0"),
        invariant=Formula("N >= 1 and R * dfact(2 * N) == dfact(2 * N0)"),
        post=Formula("R == dfact(2 * N0)"),
        variant=Formula("N"),
        domains={"N": (1, 4), "N0": (1, 4), "R": (1, 384)},
        ghosts={"N0": "N"}
    )
    results = verify(prog, spec)
    vc3 = next(r for r in results if r.name.startswith("VC3"))
    assert vc3.checked == 0
    assert vc3.ok is False
    assert "0 станів задовольнили інваріант та вихід з циклу" in vc3.detail
    assert not all(r.ok for r in results)


test_verifier_missing_domain_variable_raises_error = test_spec_validate_missing_invariant_var
test_verifier_inverted_domain_range_raises_error = test_spec_validate_invalid_range_min_greater_max
test_verifier_empty_domain_raises_error = test_spec_validate_empty_domains


def test_spec_validate_pre_var_must_be_in_inputs():
    with pytest.raises(ValueError, match="передумова .* містить змінні .* які відсутні у списку inputs"):
        Spec(
            inputs=["N"],
            pre=Formula("Nn >= 0"),
            invariant=Formula("R == 1"),
            post=Formula("R == 1"),
            domains={"N": (0, 4), "Nn": (0, 4), "R": (1, 10)}
        )


def test_verifier_missing_program_var_in_domains():
    prog = parse("begin R := 1; while N > 0 do N := N - 1 end")
    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("N >= 0"),
        post=Formula("N == 0"),
        domains={"N": (0, 4)}
    )
    with pytest.raises(ValueError, match="змінні програми .* відсутні у domains"):
        verify(prog, spec)


def test_formula_missing_var_raises_value_error():
    f = Formula("X + Y > 0")
    with pytest.raises(ValueError, match="невідома змінна"):
        f({"X": 5})


def test_formula_math_library():
    st = {"A": 24, "B": 36, "N": 6}
    assert Formula("gcd(A, B) == 12")(st) is True
    assert Formula("fib(N) == 8")(st) is True
    assert Formula("isqrt(B) == 6")(st) is True
    assert Formula("fact(4) == 24")(st) is True
    assert Formula("dfact(5) == 15")(st) is True
    assert Formula("pow(2, 3) == 8")(st) is True


def test_split_loop_diagnostics():
    prog2 = parse("begin while X > 0 do skip; while Y > 0 do skip end")
    with pytest.raises(ValueError, match="рівно один цикл while.*знайдено: 2"):
        verify(prog2, Spec(inputs=["X", "Y"], pre=Formula("X > 0"), invariant=Formula("X > 0"),
                           post=Formula("X == 0"), domains={"X": (0, 1), "Y": (0, 1)}))


def test_collect_variables_inside_if():
    from sipl.semantics.verifier import collect_variables
    prog = parse("begin if Q > 0 then R := S else skip end")
    assert collect_variables(prog) == {"Q", "R", "S"}


def test_verifier_variable_inside_if_missing_from_domains():
    prog = parse(
        "begin R := 1; while N > 0 do begin if Q > 0 then R := R * 2 else skip; N := N - 1 end end"
    )
    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("N >= 0"),
        post=Formula("N == 0"),
        domains={"N": (0, 4), "R": (1, 16)},
    )
    with pytest.raises(ValueError, match="змінні програми .* відсутні у domains"):
        verify(prog, spec)


def test_verifier_without_variant_skips_vc4():
    prog = parse("begin R := 1; while N > 0 do begin R := R * 2; N := N - 1 end end")
    spec = Spec(
        inputs=["N"],
        pre=Formula("N >= 0"),
        invariant=Formula("N >= 0 and R >= 1"),
        post=Formula("N == 0"),
        domains={"N": (0, 3), "R": (1, 8)},
    )
    results = verify(prog, spec)
    assert all(r.ok for r in results)
    assert "пропущено" in results[3].detail
