from __future__ import annotations
import html
import json
from lark import Tree, Token

MID = "|-- "
LAST = "\\-- "


def _get_span_str(node) -> str:
    if isinstance(node, Tree) and hasattr(node, "meta"):
        m = node.meta
        sl = getattr(m, "line", 1)
        sc = getattr(m, "column", 1)
        el = getattr(m, "end_line", sl)
        ec = getattr(m, "end_column", sc)
        return f"{sl}:{sc}-{el}:{ec}"
    elif isinstance(node, Token):
        l = getattr(node, "line", 1)
        c = getattr(node, "column", 1)
        el = getattr(node, "end_line", l)
        ec = getattr(node, "end_column", c + len(node.value))
        return f"{l}:{c}-{el}:{ec}"
    return ""


def to_text(node, prefix: str = "", is_last: bool = True) -> str:
    span = _get_span_str(node)
    span_txt = f" [{span}]" if span else ""
    if isinstance(node, Tree):
        name = str(node.data)
        line = f"{prefix}{LAST if is_last else MID}{name}{span_txt}\n"
        child_prefix = prefix + ("    " if is_last else "|   ")
        children = node.children
        for i, child in enumerate(children):
            line += to_text(child, child_prefix, i == len(children) - 1)
        return line
    else:
        name = f"'{node.value}' ({node.type})"
        return f"{prefix}{LAST if is_last else MID}{name}{span_txt}\n"


def to_dict(node, node_id: list[int] | None = None) -> dict:
    if node_id is None:
        node_id = [0]
    node_id[0] += 1
    span = _get_span_str(node)
    if isinstance(node, Tree):
        return {
            "id": node_id[0],
            "kind": "nonterminal",
            "name": str(node.data),
            "span": span,
            "children": [to_dict(c, node_id) for c in node.children]
        }
    else:
        return {
            "id": node_id[0],
            "kind": "terminal",
            "type": node.type,
            "value": str(node.value),
            "span": span,
            "children": []
        }


def to_json(node, indent: int = 2) -> str:
    return json.dumps(to_dict(node), ensure_ascii=False, indent=indent)


def to_dot(node) -> str:
    lines = ["digraph ParseTree {", "  node [shape=box, style=rounded, fontname=\"Helvetica\", fontsize=10];"]
    counter = [0]

    def walk(n) -> int:
        counter[0] += 1
        curr_id = counter[0]
        span = _get_span_str(n)
        span_str = f"\\n[{span}]" if span else ""
        if isinstance(n, Tree):
            label = f"{n.data}{span_str}"
            lines.append(f"  n{curr_id} [label=\"{label}\", fillcolor=\"#eef2ff\", style=\"filled,rounded\"];")
            for c in n.children:
                cid = walk(c)
                lines.append(f"  n{curr_id} -> n{cid};")
        else:
            val = str(n.value).replace('"', '\\"')
            label = f"'{val}'\\n({n.type}){span_str}"
            lines.append(f"  n{curr_id} [label=\"{label}\", fillcolor=\"#ecfdf5\", style=\"filled,rounded\"];")
        return curr_id

    walk(node)
    lines.append("}")
    return "\n".join(lines)


def to_svg(node) -> str:
    leaves = [0]
    positions = {}

    def layout(n, depth=0):
        if isinstance(n, Tree) and n.children:
            child_xs = []
            for c in n.children:
                child_xs.append(layout(c, depth + 1))
            x = sum(child_xs) / len(child_xs)
        else:
            leaves[0] += 1
            x = leaves[0] * 90
        y = depth * 70 + 40
        positions[id(n)] = (x, y)
        return x

    layout(node, 0)
    width = max(pos[0] for pos in positions.values()) + 100
    height = max(pos[1] for pos in positions.values()) + 60

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {int(width)} {int(height)}" '
        f'width="{int(width)}" height="{int(height)}" style="background:#ffffff;font-family:sans-serif;">',
        '<defs>',
        '  <style>',
        '    .edge { stroke: #94a3b8; stroke-width: 1.5; }',
        '    .nt-box { fill: #eff6ff; stroke: #3b82f6; stroke-width: 1.5; rx: 5; }',
        '    .t-box { fill: #f0fdf4; stroke: #22c55e; stroke-width: 1.5; rx: 5; }',
        '    .node-text { font-size: 11px; font-weight: bold; fill: #1e293b; text-anchor: middle; }',
        '    .span-text { font-size: 8px; fill: #64748b; text-anchor: middle; }',
        '  </style>',
        '</defs>'
    ]

    def draw_edges(n):
        if isinstance(n, Tree):
            px, py = positions[id(n)]
            for c in n.children:
                cx, cy = positions[id(c)]
                svg_lines.append(f'<line class="edge" x1="{px}" y1="{py+15}" x2="{cx}" y2="{cy-15}" />')
                draw_edges(c)

    draw_edges(node)

    def draw_nodes(n):
        x, y = positions[id(n)]
        span = _get_span_str(n)
        if isinstance(n, Tree):
            label = str(n.data)
            box_cls = "nt-box"
        else:
            label = f"'{n.value}'"
            box_cls = "t-box"

        w = max(70, len(label) * 8 + 14)
        h = 32
        bx = x - w / 2
        by = y - h / 2

        svg_lines.append(f'<rect class="{box_cls}" x="{bx}" y="{by}" width="{w}" height="{h}" />')
        esc_label = html.escape(label)
        svg_lines.append(f'<text class="node-text" x="{x}" y="{y-1}">{esc_label}</text>')
        if span:
            svg_lines.append(f'<text class="span-text" x="{x}" y="{y+11}">[{html.escape(span)}]</text>')

        if isinstance(n, Tree):
            for c in n.children:
                draw_nodes(c)

    draw_nodes(node)
    svg_lines.append('</svg>')
    return "\n".join(svg_lines)
