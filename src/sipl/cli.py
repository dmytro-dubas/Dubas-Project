from __future__ import annotations
import argparse
from pathlib import Path
import sys
from .parser import parse_file, parse_tree, SIPLSyntaxError
from .semantics.builder import build_term
from .semantics.evaluator import Evaluator, fmt_state
from .semantics.verifier import Spec, verify
from .visualization import tree as vis_tree


def parse_state(s: str) -> dict[str, int]:
    out = {}
    for part in filter(None, (p.strip() for p in s.split(","))):
        if "=" not in part:
            raise ValueError(f"невірний формат стану '{part}', очікується 'ЗМІННА=ЧИСЛО', наприклад 'N=2'")
        k, v = part.split("=", 1)
        try:
            out[k.strip()] = int(v.strip())
        except ValueError:
            raise ValueError(f"значення змінної '{k.strip()}' має бути цілим числом, отримано '{v.strip()}'")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sipl", description="SIPL Language Toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="Синтаксичний аналіз та перевірка span")
    p_parse.add_argument("file", help="Шлях до файлу .sipl")

    p_tree = sub.add_parser("tree", help="Візуалізація дерева виводу")
    p_tree.add_argument("file", help="Шлях до файлу .sipl")
    p_tree.add_argument("--format", choices=["text", "json", "dot", "svg"], default="text",
                        help="Формат виводу: text, json, dot, svg")
    p_tree.add_argument("--tokens", action="store_true",
                        help="Включати всі термінальні токени мови у дерево виводу")
    p_tree.add_argument("--out", help="Файл для збереження результату")

    p_term = sub.add_parser("term", help="Побудова семантичного терму в нотації курсу")
    p_term.add_argument("file", help="Шлях до файлу .sipl")

    p_eval = sub.add_parser("eval", help="Обчислення терму на стані змінних")
    p_eval.add_argument("file", help="Шлях до файлу .sipl")
    p_eval.add_argument("--state", default="", help="Початковий стан, наприклад N=2, X=5")
    p_eval.add_argument("--trace", action="store_true", help="Виводити покрокову таблицю перетворень")
    p_eval.add_argument("--max-steps", type=int, default=1000, help="Ліміт кроків для захисту від зациклення")

    p_ver = sub.add_parser("verify", help="Асистент доведення коректності циклу")
    p_ver.add_argument("file", help="Шлях до файлу .sipl")
    p_ver.add_argument("--spec", required=True, help="Шлях до файлу специфікації .spec.json")

    a = ap.parse_args(argv)

    try:
        if a.cmd == "tree":
            src = Path(a.file).read_text(encoding="utf-8")
            cst = parse_tree(src, keep_tokens=a.tokens)
            if a.format == "text":
                out = vis_tree.to_text(cst)
            elif a.format == "json":
                out = vis_tree.to_json(cst)
            elif a.format == "dot":
                out = vis_tree.to_dot(cst)
            elif a.format == "svg":
                out = vis_tree.to_svg(cst)

            if a.out:
                Path(a.out).write_text(out, encoding="utf-8")
                print(f"[OK] Дерево виводу успішно збережено у {a.out}")
            else:
                print(out)
            return 0

        prog = parse_file(a.file)

        if a.cmd == "parse":
            print(f"[OK] Синтаксично коректно. Span програми: {prog.span}")
            return 0

        if a.cmd == "term":
            print(build_term(prog))
            return 0

        if a.cmd == "eval":
            r = Evaluator(a.max_steps).run(build_term(prog), parse_state(a.state))
            if a.trace:
                for t in r.trace:
                    print(f"{t.n:>3} {t.rule:<12} {t.detail:<40} {fmt_state(t.before)} => {fmt_state(t.after)}")
            if r.status == "defined":
                print(fmt_state(r.state))
                return 0
            else:
                print(f"_|_ невизначено: {r.reason}")
                return 1

        if a.cmd == "verify":
            results = verify(prog, Spec.from_json(a.spec))
            for v in results:
                print(f"[{'OK' if v.ok else 'FAIL'}] {v.name}  перевірено станів: {v.checked} {v.detail}")
                if v.formula:
                    print("      умова:", v.formula)
                if v.counterexample:
                    print("      контрприклад:", v.counterexample)
            return 0 if all(v.ok for v in results) else 1

        return 0

    except SIPLSyntaxError as e:
        print(e.render(), file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        filename = getattr(e, "filename", None) or getattr(a, "file", "") or getattr(a, "spec", "")
        print(f"Помилка: файл '{filename}' не знайдено", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Помилка: {e}", file=sys.stderr)
        return 1
    except RecursionError:
        print("Помилка: перевищено ліміт вкладеності виразів, програма надто глибока", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Помилка виконання: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
