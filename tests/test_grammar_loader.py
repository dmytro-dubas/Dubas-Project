from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from lark import Tree
import sipl.parser as parser
from sipl.parser import parse_tree, parse, _load_grammar, _GRAMMAR


def test_fallback_repo_missing_uses_pkg():
    orig_is_file = Path.is_file

    def mock_is_file(self):
        if "grammar" in self.parts and self.name == "sipl.lark":
            return False
        return orig_is_file(self)

    with patch.object(Path, "is_file", mock_is_file):
        content = _load_grammar()
        assert 'start: "begin" stm "end"' in content


def test_fallback_pkg_missing_uses_importlib_resources():
    orig_is_file = Path.is_file

    def mock_is_file(self):
        if self.name == "sipl.lark":
            return False
        return orig_is_file(self)

    mock_res = MagicMock()
    mock_res.is_file.return_value = True
    mock_res.read_text.return_value = 'start: "begin" stm "end" // mock_importlib'

    with patch.object(Path, "is_file", mock_is_file):
        with patch("importlib.resources.files") as mock_files:
            mock_files.return_value.joinpath.return_value = mock_res
            content = _load_grammar()
            assert "mock_importlib" in content
            mock_files.assert_called_once_with("sipl")
            mock_res.is_file.assert_called_once()


def test_fallback_all_missing_raises_filenotfound():
    orig_is_file = Path.is_file

    def mock_is_file(self):
        if self.name == "sipl.lark":
            return False
        return orig_is_file(self)

    mock_res = MagicMock()
    mock_res.is_file.return_value = False

    with patch.object(Path, "is_file", mock_is_file):
        with patch("importlib.resources.files") as mock_files:
            mock_files.return_value.joinpath.return_value = mock_res
            with pytest.raises(FileNotFoundError) as exc_info:
                _load_grammar()
            assert "Граматику sipl.lark не знайдено" in str(exc_info.value)


def test_fallback_importlib_exception_raises_filenotfound():
    orig_is_file = Path.is_file

    def mock_is_file(self):
        if self.name == "sipl.lark":
            return False
        return orig_is_file(self)

    with patch.object(Path, "is_file", mock_is_file):
        with patch("importlib.resources.files", side_effect=ModuleNotFoundError("No module sipl")):
            with pytest.raises(FileNotFoundError) as exc_info:
                _load_grammar()
            assert "Граматику sipl.lark не знайдено" in str(exc_info.value)


def test_consistency_detects_mutation():
    repo_root = Path(__file__).resolve().parent.parent
    grammar_repo = repo_root / "grammar" / "sipl.lark"
    grammar_pkg = repo_root / "src" / "sipl" / "sipl.lark"

    text_repo = grammar_repo.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    text_pkg = grammar_pkg.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

    assert text_repo == text_pkg

    tampered_repo = text_repo + "\n// modified"
    assert tampered_repo != text_pkg

    tampered_pkg = text_pkg.replace("start:", "start_modified:")
    assert text_repo != tampered_pkg


def test_parsing_complex_boundary_expressions():
    tree1 = parse_tree("begin X := A - B - C + D * E * F end")
    assert isinstance(tree1, Tree)
    assert tree1.data == "program"

    ast1 = parse("begin X := A - B - C + D * E * F end")
    assert ast1.body.expr.op == "+"
    assert ast1.body.expr.left.op == "-"
    assert ast1.body.expr.left.left.op == "-"
    assert ast1.body.expr.right.op == "*"
    assert ast1.body.expr.right.left.op == "*"

    tree2 = parse_tree("begin if not A >= B and C <= D or not E = F and true then skip else skip end")
    assert isinstance(tree2, Tree)
    assert tree2.data == "program"

    code_deep = """begin
      while not (X = 0) do
      begin
        if X > 10 then
        begin
          while Y < 5 do
          begin
            Y := Y + 1;
            skip
          end
        end
        else
        begin
          skip
        end;
        X := X - 1
      end
    end"""
    tree3 = parse_tree(code_deep)
    assert isinstance(tree3, Tree)
    assert tree3.data == "program"


def test_parsing_all_relational_operators_in_cst():
    for op in [">=", "<=", ">", "<", "="]:
        tree = parse_tree(f"begin if X {op} 10 then skip else skip end")
        assert isinstance(tree, Tree)
        rel_nodes = list(tree.find_data("rel"))
        assert len(rel_nodes) == 1
        assert str(rel_nodes[0].children[1]) == op


def test_parsing_semicolon_precedence_and_associativity():
    ast_seq = parse("begin X := 1; Y := 2; Z := 3 end")
    assert ast_seq.body.first.var == "X"
    assert ast_seq.body.second.first.var == "Y"
    assert ast_seq.body.second.second.var == "Z"

    ast_while_seq = parse("begin while X > 0 do X := X - 1; Y := 2 end")
    assert hasattr(ast_while_seq.body, "first")
    assert hasattr(ast_while_seq.body.first, "cond")
    assert ast_while_seq.body.second.var == "Y"


def test_parsing_deeply_nested_boolean_not():
    ast_not = parse("begin if not not not not true then skip else skip end")
    c = ast_not.body.cond
    for _ in range(4):
        assert hasattr(c, "operand")
        c = c.operand
    assert c.value is True
