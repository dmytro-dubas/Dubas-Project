from pathlib import Path
from sipl.cli import main

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_cli_parse(capsys):
    ret = main(["parse", str(EXAMPLES / "variant5_double_fact.sipl")])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "[OK]" in out


def test_cli_term(capsys):
    ret = main(["term", str(EXAMPLES / "variant5_double_fact.sipl")])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "AS_R(1)" in out
    assert "WH(S2(gr, N=>, 0)" in out


def test_cli_eval(capsys):
    ret = main(["eval", str(EXAMPLES / "variant5_double_fact.sipl"), "--state", "N=2", "--trace"])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "AF_AS" in out
    assert "AF_SEQ" in out
    assert "AF_WH_TRUE" in out
    assert "[N -> 0, R -> 8]" in out


def test_cli_eval_infinite_loop(capsys):
    ret = main(["eval", str(EXAMPLES / "infinite_loop.sipl"), "--max-steps", "20"])
    out, _ = capsys.readouterr()
    assert ret == 1
    assert "невизначено" in out


def test_cli_tree_text(capsys):
    ret = main(["tree", str(EXAMPLES / "variant5_double_fact.sipl"), "--format", "text"])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "program" in out


def test_cli_tree_svg(tmp_path):
    svg_out = tmp_path / "tree.svg"
    ret = main(["tree", str(EXAMPLES / "variant5_double_fact.sipl"), "--format", "svg", "--out", str(svg_out)])
    assert ret == 0
    assert svg_out.exists()
    assert "<svg" in svg_out.read_text(encoding="utf-8")


def test_cli_verify_ok(capsys):
    ret = main(["verify", str(EXAMPLES / "variant5_double_fact.sipl"), "--spec", str(EXAMPLES / "variant5_double_fact.spec.json")])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "[OK] VC1" in out
    assert "[OK] VC2" in out
    assert "[OK] VC3" in out
    assert "[OK] VC4" in out


def test_cli_verify_fail(capsys):
    ret = main(["verify", str(EXAMPLES / "variant5_double_fact.sipl"), "--spec", str(EXAMPLES / "variant5_incorrect.spec.json")])
    out, _ = capsys.readouterr()
    assert ret == 1
    assert "[FAIL] VC2" in out
    assert "контрприклад:" in out


def test_cli_verify_vacuous(capsys, tmp_path):
    import json
    spec_data = {
        "inputs": ["N"],
        "pre": "N > 100",
        "invariant": "R * dfact(2 * N) == dfact(2 * N0)",
        "post": "R == dfact(2 * N0)",
        "variant": "N",
        "domains": {"N": [0, 4], "N0": [1, 4], "R": [1, 384]},
        "ghosts": {"N0": "N"}
    }
    spec_file = tmp_path / "vacuous.spec.json"
    spec_file.write_text(json.dumps(spec_data), encoding="utf-8")
    ret = main(["verify", str(EXAMPLES / "variant5_double_fact.sipl"), "--spec", str(spec_file)])
    out, _ = capsys.readouterr()
    assert ret == 1
    assert "[FAIL] VC1" in out
    assert "перевірено станів: 0" in out


def test_cli_tree_with_tokens(capsys):
    ret = main(["tree", str(EXAMPLES / "variant5_double_fact.sipl"), "--tokens", "--format", "text"])
    out, _ = capsys.readouterr()
    assert ret == 0
    assert "program" in out
    assert "'begin'" in out
    assert "';'" in out
    assert "':='" in out


def test_cli_file_not_found_clean_message(capsys):
    ret = main(["parse", "no_such_file.sipl"])
    _, err = capsys.readouterr()
    assert ret == 1
    assert "Помилка: файл 'no_such_file.sipl' не знайдено" in err
    assert "Traceback" not in err


def test_cli_invalid_state_clean_message(capsys):
    ret = main(["eval", str(EXAMPLES / "factorial.sipl"), "--state", "N"])
    _, err = capsys.readouterr()
    assert ret == 1
    assert "Помилка: невірний формат стану 'N'" in err
    assert "Traceback" not in err


def test_cli_invalid_syntax_lists_semicolon(capsys):
    ret = main(["parse", str(EXAMPLES / "invalid_syntax.sipl")])
    _, err = capsys.readouterr()
    assert ret == 2
    assert "';'" in err
    assert "Traceback" not in err

