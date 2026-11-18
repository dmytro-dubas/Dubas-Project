Курсовий проєкт, Теорія програмування
Дубас Дмитро Олександрович, ТК-32

## Завдання
Трек Формальна семантика

CORE-02: парсер і AST з позиціями, 1.5
VIS-01: дерево виводу, 1.5
SEM-01: семантичний терм, 2.0
SEM-02: обчислення терму з trace, 2.0
SEM-04: перевірка інваріанта циклу, 2.5
REL-02: release, SemVer, 0.5

Разом: 10.0


## Структура
grammar/sipl.lark   граматика
src/sipl/
    span.py
    ast.py
    parser.py   парсер
    visualization/tree.py   дерево виводу
    semantics/
        terms.py
        builder.py
        evaluator.py
        verifier.py
    cli.py  командний рядок
examples/   приклади
tests/  тести
docs/
dist/


## Встановлення
python -m pip install -e ".[dev]"


## Тести
python -m pytest tests


## Команди
Перевірка синтаксису:

python -m sipl.cli parse examples/variant5_double_fact.sipl

Дерево виводу, формати text, json, dot, svg:

python -m sipl.cli tree examples/variant5_double_fact.sipl --format text
python -m sipl.cli tree examples/variant5_double_fact.sipl --format svg --out tree.svg

Усі термінали в дереві:

python -m sipl.cli tree examples/variant5_double_fact.sipl --tokens --format text

Семантичний терм:

python -m sipl.cli term examples/variant5_double_fact.sipl

Обчислення на стані з trace:

python -m sipl.cli eval examples/variant5_double_fact.sipl --state "N=2" --trace

Ліміт кроків:

python -m sipl.cli eval examples/infinite_loop.sipl --max-steps 50

Перевірка інваріанта:

python -m sipl.cli verify examples/variant5_double_fact.sipl --spec examples/variant5_double_fact.spec.json

Приклад з неправильним інваріантом, виводить контрприклад:

python -m sipl.cli verify examples/variant5_double_fact.sipl --spec examples/variant5_incorrect.spec.json


## Збірка
python -c "import os; from setuptools import build_meta as b; os.makedirs('dist', exist_ok=True); b.build_wheel('dist'); b.build_sdist('dist')"

