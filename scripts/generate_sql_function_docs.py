#!/usr/bin/env python3

from dataclasses import dataclass, field
import duckdb
import re
import operator


@dataclass(order=True)
class DocFunction:
    name: str
    parameters: list[str]
    description: str
    examples: list[str]
    category: str
    is_variadic: bool = False
    aliases: list[str] = field(default_factory=list)
    fixed_example_results: list[str] = field(default_factory=list)
    nr_optional_arguments: int = 0


DOC_VERSION = 'preview'
DOC_FILES = [
    f'docs/{DOC_VERSION}/sql/functions/blob.md',
    f'docs/{DOC_VERSION}/sql/functions/text.md',
]

# 'functions' that are binary operators are listed between the arguments
BINARY_OPERATORS = ['||', '^@', 'LIKE', 'SIMILAR TO']
EXTRACT_OPERATOR = '[]'

# override/add to duckdb_functions() outputs:
# NOTE: duckdb_functions() only contains sufficient information for scalar and aggregate functions.
OVERRIDES: list[DocFunction] = [
    # table functions
    DocFunction(
        category='blob',
        name='read_blob',
        parameters=['source'],
        description="Returns the content from `source` (a filename, a list of filenames, or a glob pattern) as a `BLOB`. See the `read_blob` guide for more details.",
        examples=["read_blob('hello.bin')"],
        fixed_example_results=[r"hello\x0A"],
    ),
    DocFunction(
        category='string',
        name='read_text',
        parameters=['source'],
        description="Returns the content from `source` (a filename, a list of filenames, or a glob pattern) as a `VARCHAR`. The file content is first validated to be valid UTF-8. If `read_text` attempts to read a file with invalid UTF-8 an error is thrown suggesting to use `read_blob` instead. See the `read_text` guide for more details.",
        examples=["read_text('hello.txt')"],
        fixed_example_results=["hello\\n"],
    ),
    # macros
    DocFunction(
        category='string',
        name='md5_number_lower',
        parameters=['string'],
        description="Returns the lower 64-bit segment of the MD5 hash of the `string` as a `UBIGINT`.",
        examples=["md5_number_lower('abc')"],
    ),
    DocFunction(
        category='string',
        name='md5_number_upper',
        parameters=['string'],
        description="Returns the upper 64-bit segment of the MD5 hash of the `string` as a `UBIGINT`.",
        examples=["md5_number_upper('abc')"],
    ),
    DocFunction(
        category='regex',
        name='regexp_split_to_table',
        parameters=['string', 'regex'],
        description="Splits the `string` along the `regex` and returns a row for each part.",
        examples=["regexp_split_to_table('hello world; 42', ';? ')"],
    ),
    DocFunction(
        category='string',
        name='split_part',
        parameters=['string', 'separator', 'index'],
        description="Splits the `string` along the `separator` and returns the data at the (1-based) `index` of the list. If the `index` is outside the bounds of the list, return an empty string (to match PostgreSQL's behavior).",
        examples=["split_part('a;b;c', ';', 2)"],
    ),
    # others
    DocFunction(
        category='string',
        name='[]',
        parameters=['string', 'index'],
        description="Extracts a single character using a (1-based) index.",
        examples=["'DuckDB'[4]"],
        aliases=['array_extract'],
    ),
    DocFunction(
        category='string',
        name='[]',
        parameters=['string', 'begin', 'end'],
        description='Extracts a string using slice conventions similar to Python. Missing `begin` or `end` arguments are interpreted as the beginning or end of the list respectively. Negative values are accepted.',
        examples=["'DuckDB'[:4]"],
        aliases=['array_slice'],
    ),
    DocFunction(
        category='string',
        name='LIKE',
        parameters=['string', 'target'],
        description='Returns `true` if the `string` matches the like specifier (see Pattern Matching).',
        examples=["'hello' LIKE '%lo'"],
    ),
    DocFunction(
        category='string',
        name='SIMILAR TO',
        parameters=['string', 'regex'],
        description="Returns `true` if the `string` matches the `regex` (see Pattern Matching).",
        examples=["'hello' SIMILAR TO 'l+'"],
        aliases=['regexp_full_match'],
    ),
    DocFunction(
        category='string',
        name='position',  # non-standard parsing with 'IN' as pseudo argument
        parameters=['search_string IN string'],
        description="Return location of first occurrence of `search_string` in `string`, counting from 1. Returns 0 if no match found.",
        examples=["position('b' IN 'abc')"],
        aliases=['instr', 'strpos'],
    ),
    DocFunction(
        category='string',
        name='^@',  # edge case: alias between operator and regular function
        parameters=['string', 'search_string'],
        description="Returns `true` if `string` begins with `search_string`.",
        examples=["'abc' ^@ 'a'"],
        aliases=['starts_with'],
    ),
]

# NOTE: All function aliases are added, unless explicitly excluded. Format: (<category>, <function_name>)
EXCLUDES = [('string', 'list_slice')]

PAGE_LINKS = {
    # intra-page links:
    '`concat(arg1, arg2, ...)`': "#concatvalue",
    'operator `||`': "#arg1--arg2",
    'fmt syntax': "#fmt-syntax",
    'printf syntax': '#printf-syntax',
    # links to other doc pages:
    '`list_concat(list1, list2)`': f'docs/{DOC_VERSION}/sql/functions/list.md#list_concatlist1-list2',
    '`read_blob` guide': f'docs/{DOC_VERSION}/guides/file_formats/read_file.md#read_blob',
    '`read_text` guide': f'docs/{DOC_VERSION}/guides/file_formats/read_file.md#read_text',
    'slicing': f'docs/{DOC_VERSION}/sql/functions/list.md#slicing',
    'slice conventions': f'docs/{DOC_VERSION}/sql/functions/list.md#slicing',
    'Pattern Matching': f'docs/{DOC_VERSION}/sql/functions/pattern_matching.md',
    'collations': f'docs/{DOC_VERSION}/sql/expressions/collations.md',
    'regex `options`': f'docs/{DOC_VERSION}/sql/functions/regular_expressions.md#options-for-regular-expression-functions',
    # external page links:
    '`os.path.dirname`': 'https://docs.python.org/3.7/library/os.path.html#os.path.dirname',
    '`os.path.basename`': 'https://docs.python.org/3.7/library/os.path.html#os.path.basename',
    '`pathlib.parts`': 'https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.parts',
    '`re.escape` function': 'https://docs.python.org/3/library/re.html#re.escape',
    'Percent-Encoding': 'https://datatracker.ietf.org/doc/html/rfc3986#section-2.1',
}


def main():
    for doc_file in DOC_FILES:
        print(f"creating file {doc_file} ...")
        with open(doc_file, "r") as f:
            doc_text = f.read()
        block_endline = "<!-- End of section generated by scripts/generate_sql_function_docs.py -->\n"
        for current_block, startline, categories in get_function_blocks(
            doc_text, block_endline
        ):
            function_data = get_function_data(categories)
            updated_block = (
                startline
                + generate_docs_table(function_data)
                + generate_docs_records(function_data)
                + block_endline
            )
            doc_text = doc_text.replace(current_block, updated_block)
        with open(doc_file, "w+") as f:
            f.write(doc_text)


# returns (full_block_content, startline, categories) per function block in the file
def get_function_blocks(
    doc_text: str, block_endline: str
) -> list[tuple[list[str], str, str]]:
    startline_regex = r"(<!-- Start of section generated by scripts/generate_sql_function_docs.py; categories: \[)(.*?)(\] -->\n)"
    block_regex = startline_regex + "(.*?)" + f"({block_endline})"
    function_blocks: list[tuple[str, str, str, str, str]] = re.findall(
        block_regex, doc_text, re.DOTALL
    )
    # regex groups: 0,1,2 = startline; group 3 = block content, group 4 = endline
    if not function_blocks or any(
        len(block_groups) != 5 for block_groups in function_blocks
    ):
        print(f"ERROR: doc generation failed, start or end line missing in file")
        exit(1)
    function_blocks_info = []
    for block_groups in function_blocks:
        full_block_content = ''.join(block_groups)
        startline = ''.join(block_groups[:3])
        categories = [category.strip() for category in block_groups[1].split(',')]
        function_blocks_info.append((full_block_content, startline, categories))
    return function_blocks_info


def get_function_data(categories: list[str]) -> list[DocFunction]:
    query = function_data_query(categories)
    function_data: list[DocFunction] = [
        DocFunction(*func) for func in duckdb.sql(query).fetchall()
    ]
    function_data = apply_overrides(function_data, categories)
    function_data = sort_function_data(function_data)
    function_data = prune_duplicates(function_data)
    function_data = [apply_url_conversions(function) for function in function_data]
    return function_data


def function_data_query(categories: str) -> str:
    return f"""
with categories as (select unnest({categories}) category)
select distinct
  f1.function_name,
  f1.parameters,
  f1.description,
  f1.examples,
  categories.category,
  f1.varargs='ANY' as is_variadic,
  list_sort(list_distinct(list(f2.function_name))) as aliases,
  list_value() fixed_example_results
from
  categories
  join duckdb_functions() f1 on list_contains(f1.categories, categories.category)
  left join duckdb_functions() f2 on (
    f1.alias_of = f2.function_name
    or f1.function_name = f2.alias_of
    or (f1.alias_of = f2.alias_of and f1.function_name != f2.function_name)
  )
group by all
order by all
"""


def apply_overrides(function_data: list[DocFunction], categories: list[str]):
    function_data = [
        func
        for func in function_data
        if not any(
            func.category == override.category and func.name == override.name
            for override in OVERRIDES
        )
        and (func.category, func.name) not in EXCLUDES
    ]
    function_data += [
        override for override in OVERRIDES if override.category in categories
    ]
    return function_data


def sort_function_data(function_data: list[DocFunction]):
    function_data_1 = sorted(
        [func for func in function_data if func.name == EXTRACT_OPERATOR],
        key=operator.attrgetter("name", "description", "parameters"),
    )
    function_data_2 = sorted(
        [func for func in function_data if func.name in BINARY_OPERATORS],
        key=operator.attrgetter("name", "description", "parameters"),
    )
    function_data_3 = sorted(
        [
            func
            for func in function_data
            if (func.name not in BINARY_OPERATORS) and (func.name != EXTRACT_OPERATOR)
        ],
        key=operator.attrgetter("name", "description", "parameters"),
    )
    return function_data_1 + function_data_2 + function_data_3


# remove duplicates with optional parameters
def prune_duplicates(function_data: list[DocFunction]):
    for idx_func, func in enumerate(function_data):
        if idx_func == 0:
            continue
        if (
            func.name == function_data[idx_func - 1].name
            and function_data[idx_func - 1].description == func.description
        ):
            if function_data[idx_func - 1].parameters == func.parameters[:-1]:
                func.nr_optional_arguments = (
                    function_data[idx_func - 1].nr_optional_arguments + 1
                )
                function_data[idx_func - 1].name = "DELETE_ME"
            elif all(
                param in function_data[idx_func - 1].parameters
                for param in func.parameters
            ):
                func.name = "DELETE_ME"
    return [func for func in function_data if func.name != "DELETE_ME"]


def apply_url_conversions(function: DocFunction):
    for link_text in PAGE_LINKS:
        if link_text in function.description:
            if PAGE_LINKS[link_text].startswith('http'):
                # external link
                url = f"{PAGE_LINKS[link_text]}"
            else:
                # internal link
                page, _, section = PAGE_LINKS[link_text].partition('#')
                url = ''
                if page:
                    url = "{% " + f"link {page}" + " %}"
                if section:
                    url += f"#{section}"
            function.description = function.description.replace(
                link_text, f"[{link_text}]({url})"
            )
    return function


def generate_docs_table(function_data: list[DocFunction]):
    table_str = "<!-- markdownlint-disable MD056 -->\n\n"
    table_str += "| Name | Description |\n|:--|:-------|\n"
    for func in function_data:
        if not func.examples:
            print(f"WARNING (skipping): '{func.name}' - no example is available")
            continue
        func_title = get_function_title(func)
        anchor = get_anchor_from_title(func_title)
        table_str += f"| [`{func_title}`](#{anchor}) | {func.description} |\n"
    table_str += "\n<!-- markdownlint-enable MD056 -->\n"
    return table_str


def generate_docs_records(function_data: list[DocFunction]):
    record_str = "\n"
    for func in function_data:
        if not func.examples:
            print(f"skipping {func.name}")
            continue
        record_str += f"#### `{get_function_title(func)}`\n\n"
        record_str += '<div class="nostroke_table"></div>\n\n'
        record_str += f"| **Description** | {func.description} |\n"
        record_str += generate_example_rows(func)
        if func.aliases:
            aliases = ', '.join(f"`{alias}`" for alias in func.aliases)
            record_str += f"| **{'Alias' if len(func.aliases) == 1 else 'Aliases'}** | {aliases} |\n"
        record_str += '\n'
    return record_str


def get_function_title(func: DocFunction):
    if func.name in BINARY_OPERATORS:
        assert len(func.parameters) == 2
        function_title = f"{func.parameters[0]} {func.name} {func.parameters[1]}"
    elif func.name == EXTRACT_OPERATOR:
        assert len(func.parameters) >= 2
        parameter_str = ":".join(func.parameters[1:])
        function_title = f"{func.parameters[0]}[{parameter_str}]"
    else:
        if func.nr_optional_arguments == 0:
            parameter_str = (
                f"{", ".join(func.parameters)}{', ...' if (func.is_variadic) else ''}"
            )
        else:
            mandatory_args = func.parameters[: -1 * func.nr_optional_arguments]
            optional_args = func.parameters[-1 * func.nr_optional_arguments :]
            parameter_str = f"{", ".join(mandatory_args)}{"".join(f"[, {arg}]" for arg in optional_args)}"
        function_title = f"{func.name}({parameter_str})"
    return function_title


def get_anchor_from_title(title: str):
    return re.sub(r'[\(\)\[\]\.,$@|:^]+', '', title.lower().replace(' ', '-'))


def generate_example_rows(func: DocFunction):
    lines = ''
    for idx, example in enumerate(func.examples):
        example_result = (
            func.fixed_example_results[idx] if func.fixed_example_results else ''
        )
        example_num = ' ' + str(idx + 1) if len(func.examples) > 1 else ''
        lines += f"| **Example{example_num}** | `{example}` |\n"
        if not example_result:
            try:
                if func.name in BINARY_OPERATORS:
                    example = f"({example})"
                run_example = re.sub(r'␣', ' ', example)
                query_result = duckdb.sql(rf"select {run_example}::VARCHAR").fetchall()
                if len(query_result) != 1:
                    example_result = 'Multiple rows: ' + ', '.join(
                        (
                            f"`'{query_result[idx_result][0]}'`"
                            if query_result[idx_result][0]
                            else "`NULL`"
                        )
                        for idx_result in range(len(query_result))
                    )
                else:
                    example_result = (
                        f"{query_result[0][0]}" if query_result[0][0] else "NULL"
                    )
                    # replace leading and trailing spaces by '␣'
                    nr_leading_spaces = 0
                    nr_trailing_spaces = 0
                    while example_result and example_result[0] == ' ':
                        example_result = example_result[1:]
                        nr_leading_spaces += 1
                    while example_result and example_result[-1] == ' ':
                        example_result = example_result[:-1]
                        nr_trailing_spaces += 1
                    example_result = f"{nr_leading_spaces * '␣'}{example_result}{nr_trailing_spaces * '␣'}"
            except duckdb.ParserException as e:
                print(
                    f"Error for function '{func.name}', could not calculate example: '{example}'. Consider adding it via OVERRIDES'. {e}"
                )
        if '`' not in example_result:
            example_result = f"`{example_result}`"
        lines += f"| **Result** | {example_result} |\n"
    return lines


if __name__ == "__main__":
    main()
