import json
import xml.etree.ElementTree as ET
import pytest
from sipl.parser import parse_tree
from sipl.visualization import tree as vis_tree


SAMPLE_CODE = """begin
  R := 1;
  while N > 0 do
    N := N - 1
end"""


def test_visualization_text():
    cst = parse_tree(SAMPLE_CODE)
    txt = vis_tree.to_text(cst)
    assert "program" in txt
    assert "seq" in txt
    assert "assign" in txt
    assert "1:1" in txt


def test_visualization_json():
    cst = parse_tree(SAMPLE_CODE)
    raw = vis_tree.to_json(cst)
    data = json.loads(raw)
    assert data["kind"] == "nonterminal"
    assert data["name"] == "program"
    assert len(data["children"]) > 0


def test_visualization_dot():
    cst = parse_tree(SAMPLE_CODE)
    dot = vis_tree.to_dot(cst)
    assert dot.startswith("digraph ParseTree {")
    assert "n1 -> n2;" in dot or "->" in dot


def test_visualization_svg():
    cst = parse_tree(SAMPLE_CODE)
    svg = vis_tree.to_svg(cst)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "<rect" in svg
    assert "<text" in svg


@pytest.mark.parametrize("op,esc", [
    ("<", "&lt;"),
    ("<=", "&lt;="),
    (">", "&gt;"),
    (">=", "&gt;="),
    ("=", "="),
])
def test_visualization_svg_relational_operators(op, esc):
    cst = parse_tree(f"begin while X {op} 10 do X := X + 1 end")
    svg = vis_tree.to_svg(cst)
    assert esc in svg
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    texts = [elem.text for elem in root.iter() if elem.tag.endswith("text")]
    assert f"'{op}'" in texts


def test_visualization_svg_xml_escaping():
    cst = parse_tree("begin while X < 5 and not Y >= 2 do X := X + 1 end")
    svg = vis_tree.to_svg(cst)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "&lt;" in svg
    assert "&gt;=" in svg
    texts = {elem.text for elem in root.iter() if elem.tag.endswith("text")}
    assert "'<'" in texts
    assert "'>='" in texts


def test_visualization_svg_compound_condition():
    cst = parse_tree("begin while not (X < 5 and Y >= 2 or Z <= 0) do skip end")
    svg = vis_tree.to_svg(cst)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    texts = {elem.text for elem in root.iter() if elem.tag.endswith("text")}
    assert {"'<'", "'>='", "'<='"}.issubset(texts)
    assert {"neg", "conj", "disj"}.issubset(texts)


def test_visualization_svg_minidom_and_keep_tokens():
    import xml.dom.minidom as minidom
    cst = parse_tree("begin while X < 5 do X := X + 1 end", keep_tokens=True)
    svg = vis_tree.to_svg(cst)
    doc = minidom.parseString(svg)
    assert doc.documentElement.tagName == "svg"

