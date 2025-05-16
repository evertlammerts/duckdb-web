---
layout: docu
redirect_from:
- /docs/dev/building/python
title: Python
---

The DuckDB Python package lives in the main [DuckDB source on Github](https://github.com/duckdb/duckdb/) under the `/tools/pythonpkg/` folder. It uses [pybind11](https://pybind11.readthedocs.io/en/stable/) to create Python bindings with DuckDB.

# Building From Source

Make sure you have checked out the [DuckDB source](https://github.com/duckdb/duckdb/) and that you are in its root. E.g.:

```bash
$ git clone https://github.com/duckdb/duckdb.git
...
$ cd duckdb
```

Below are a number of options to build the python library from source, with or without debug symbols, and with a default or custom set of [extensions]({% link docs/stable/extensions/overview.md %}). Make sure to check out the [DuckDB build documentation]({% link docs/stable/dev/building/overview.md %}) if you run into trouble building the DuckDB main library.

## Prerequisite: Create and activate a Python Virtual Env

Use your favorite way to create a Python virtual environment. A virtual environment isolates dependencies and, depending on the tooling you use, givs you control over which Python interpreter you use. This way you don't pollute your system-wide Python with the different packages you need for your projects.

We strongly recommend you use a tool like [uv](https://docs.astral.sh/uv/) (or Poetry, conda, etc) for helping you manage Python interpreter versions and virtual environments. The following code exmaples use Python3's built in `venv` module.

```bash
# Create a virtual environment in the .venv folder (in the duckdb source root)
$ python3 -m venv --prompt duckdb .venv

# Activate the virtual env
$ source .venv/bin/activate
```

Make sure that your virtual env has the pip module available:

```bash
# Print pip's help
$ python3 -m pip --help
```

If that fails with `No module named pip` and you use `uv`, then run:

```bash
# Install pip
$ uv pip install pip
```

## Default release, debug build or cloud storage

The following will build the package with the default set of extensions (json, parquet, icu and core_function).

### Release build

```bash
GEN=ninja BUILD_PYTHON=1 make release
```

### Debug build

```bash
GEN=ninja BUILD_PYTHON=1 make debug
```

### Cloud Storage

You may need the package files to reside under the same prefix where the library is installed; e.g., when installing to cloud storage from a notebook.

First, get the repository based version number and extract the source distribution.

```bash
python3 -m pip install build # required for PEP 517 compliant source dists
cd tools/pythonpkg
export SETUPTOOLS_SCM_PRETEND_VERSION=$(python3 -m setuptools_scm)
pyproject-build . --sdist
cd ../..
```

Next, copy over the python package related files, and install the package.

```bash
mkdir -p $DUCKDB_PREFIX/src/duckdb-pythonpkg
tar --directory=$DUCKDB_PREFIX/src/duckdb-pythonpkg -xzpf tools/pythonpkg/dist/duckdb-${SETUPTOOLS_SCM_PRETEND_VERSION}.tar.gz
pip install --prefix $DUCKDB_PREFIX -e $DUCKDB_PREFIX/src/duckdb-pythonpkg/duckdb-${SETUPTOOLS_SCM_PRETEND_VERSION}
```

### Verify

```bash
python3 -c "import duckdb; print(duckdb.sql('SELECT 42').fetchall())"
```

## Adding extensions

Before thinking about statically linking extensions you should know that the Python package currently doesn't handle linked in extensions very well. If you don't really need to have an extension baked in than the advice is to just stick to [installing them at runtime]({% link docs/stable/extensions/installing_extensions.md %}). See `tools/pythonpkg/duckdb_extension_config.cmake` for the default list of extensions that are built with the python package. Any other extension should be considered problematic.

Having said that, if you do want to give it a try, here's how.

For more details on building DuckDB extensions look at the [documentation]({% link docs/stable/dev/building/building_extensions.md %}).

The DuckDB build process follows the following logic for building extensions:
1. First compose the complete set of extensions that might be included in the build
1. Then compose the complete set of extensions that should be excluded from the build
1. Assemble the final set of extensions to be compiled by subtracting the set of excluded extensions from the set of included extensions.

The following mechanisms add to the set of **_included_ extensions**:

| Mechanism | Syntax / Example |
| ---       | ---              |
| **Built-in extensions enabled by default** | `extension/extension_config.cmake` (≈30 built-ins) |
| **Python package extensions enabled by default** | `tools/pythonpkg/duckdb_extension_config.cmake` (`json;parquet;icu`) |
| **Semicolon-separated include list** | `DUCKDB_EXTENSIONS=fts;tpch;json` |
| **Flags** | `BUILD_TPCH=1`, `BUILD_JEMALLOC=1`, `BUILD_FTS=1`, … |
| **Presets** | `BUILD_ALL_EXT=1` - Build all in-tree extensions<br/>`BUILD_ALL_IT_EXT=1` - _Only_ build in-tree extensions<br/>`BUILD_ALL_OOT_EXT=1` - Build all out-of-tree extensions |
| **Custom config file(s)** | `DUCKDB_EXTENSION_CONFIGS=path/to/my.cmake` |
| **Core-only overrides** <br/>_only relevant with `DISABLE_BUILTIN_EXTENSIONS=1`_ | `CORE_EXTENSIONS=httpfs;fts` |

---

The following mechanisms add to the set of **_excluded_ extensions**:

| Mechanism  | Syntax / Example |
| ---        | ---              |
| **Semicolon-separated skip list** | `SKIP_EXTENSIONS=parquet;jemalloc` |
| **Flags** | `DISABLE_PARQUET=1`, `DISABLE_CORE_FUNCTIONS=1`, … |
| **“No built-ins” switch** <br/>_Throws out *every* statically linked extension **except** `core_functions`.  Use `CORE_EXTENSIONS=…` to whitelist a subset back in._ | `DISABLE_BUILTIN_EXTENSIONS=1` |

---

## Show all installed extensions

```bash
python3 -c "import duckdb; print(duckdb.sql('SELECT extension_name, installed, description FROM duckdb_extensions();'))"
```

# Development Environment Tooling

## Debugging

If you've compiled DuckDB and the Python client with debug symbols then you should be able to use `lldb` to debug the client code:



## IDE / CLion Setup

-DCMAKE_PREFIX_PATH=/Users/evert/projects/duckdb/.venv;$CMAKE_PREFIX_PATH -DPython3_EXECUTABLE=/Users/evert/projects/duckdb/.venv/bin/python3 -DENABLE_PYTHON_ANALYSIS=ON -DBUILD_PYTHON=1

## Development and Stubs

`*.pyi` stubs in `duckdb-stubs` are manually maintained. The connection-related stubs are generated using dedicated scripts in `tools/pythonpkg/scripts/`:
- `generate_connection_stubs.py`
- `generate_connection_wrapper_stubs.py`

These stubs are important for autocomplete in many IDEs, as static-analysis based language servers can't introspect `duckdb`'s binary module.

To verify the stubs match the actual implementation:
```bash
python3 -m pytest tests/stubs
```

If you add new methods to the DuckDB Python API, you'll need to manually add corresponding type hints to the stub files.

## Clang-tidy and CMakeLists

The pythonpkg does not use the CMakeLists for compilation, for that it uses pip and `package_build.py` mostly.
But we still have CMakeLists in the pythonpkg, for tidy-check and intellisense purposes.
For this reason it might not be instantly apparent that the CMakeLists are incorrectly set up, and will only result in a very confusing CI failure of TidyCheck.

To prevent this, or to help you when you encounter said CI failure, here are a couple of things to note about the CMakeLists in here.

The pythonpkg depends on `PythonLibs`, and `pybind11`, for some reason `PythonLibs` can not be found by clang-tidy when generating the `compile_commands.json` file
So the reason for clang-tidy failing is likely that there is no entry for a file in the `compile_commands.json`, check the CMakeLists to see why cmake did not register it.

Helpful information:
`clang-tidy` is not a standard binary on MacOS, and can not be installed with brew directly (doing so will try to install clang-format, and they are not the same thing)
Instead clang-tidy is part of `llvm`, so you'll need to install that (`brew install llvm`), after installing llvm you'll likely have to add the llvm binaries folder to your PATH variable to use clang-tidy
For example:

```bash
export PATH="$PATH:/opt/homebrew/Cellar/llvm/15.0.2/bin"
```

## What are py::objects and a py::handles??

These are classes provided by pybind11, the library we use to manage our interaction with the python environment.
py::handle is a direct wrapper around a raw PyObject* and does not manage any references.
py::object is similar to py::handle but it can handle refcounts.

I say *can* because it doesn't have to, using `py::reinterpret_borrow<py::object>(...)` we can create a non-owning py::object, this is essentially just a py::handle but py::handle can't be used if the prototype requires a py::object.

`py::reinterpret_steal<py::object>(...)` creates an owning py::object, this will increase the refcount of the python object and will decrease the refcount when the py::object goes out of scope.

When directly interacting with python functions that return a `PyObject*`, such as `PyDateTime_DATE_GET_TZINFO`, you should generally wrap the call in `py::reinterpret_steal` to take ownership of the returned object.

# Troubleshooting

## Pip fails with `No names found, cannot describe anything`

If you've forked DuckDB you may run into trouble when building the Python package when you haven't pulled in the tags.

```bash
# Check your remotes
git remote -v

# If you don't see upstream	git@github.com:duckdb/duckdb.git, then add it
git remote add upstream git@github.com:duckdb/duckdb.git

# Now you can pull & push the tags
git fetch --tags upstream
git push --tags
```

## Building with the httpfs extension Fails

The build fails on OSX when both the [`httpfs` extension]({% link docs/stable/extensions/httpfs/overview.md %}) and the Python package are included:

```console
ld: library not found for -lcrypto
clang: error: linker command failed with exit code 1 (use -v to see invocation)
error: command '/usr/bin/clang++' failed with exit code 1
ninja: build stopped: subcommand failed.
make: *** [release] Error 1
```

Linking in the httpfs extension is problematic. Please install it at runtime, if you can.

## Importing duckdb fails with `symbol not found in flat namespace`

If you seen an error that looks like this:

```console
ImportError: dlopen(/usr/bin/python3/site-packages/duckdb/duckdb.cpython-311-darwin.so, 0x0002): symbol not found in flat namespace '_MD5_Final'
```

... then you've probably tried to link in a problematic extension. As mentioned above: `tools/pythonpkg/duckdb_extension_config.cmake` contains the default list of extensions that are built with the python package. Any other extension might cause problems.

## Python fails with `No module named 'duckdb.duckdb'`

If you're in `tools/pythonpkg` and try to `import duckdb` you might see:

```console
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/duckdb/tools/pythonpkg/duckdb/__init__.py", line 4, in <module>
    import duckdb.functional as functional
  File "/duckdb/tools/pythonpkg/duckdb/functional/__init__.py", line 1, in <module>
    from duckdb.duckdb.functional import (
ModuleNotFoundError: No module named 'duckdb.duckdb'
```

This is because Python imported from the `duckdb` directory (i.e. `tools/pythonpkg/duckdb/`), rather than from the installed package. You should start your interpreter from a different directory instead.