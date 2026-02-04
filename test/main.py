from __future__ import annotations
from argparse import ArgumentParser
import io
import re
import sys
import inspect
import textwrap
import traceback
from types import FunctionType, ModuleType
from utility import DotMismatch, fakedots

# Modules defining tests
import core
import identifiers
import internals as internals
import render
import show
import styling

_Case = tuple[str,FunctionType]

def _get_cases(module:ModuleType) -> list[_Case]:
    mname = module.__name__
    result = []
    for name in dir(module):
        if name.startswith("test_"):
            value = getattr(module,name)
            if isinstance(value,FunctionType):
                if getattr(value,'__module__',None) == mname:
                    tname = name.removeprefix("test_")
                    result.append((mname + ":" + tname,value))
    return result


class _CapturedOutput():
    __slots__ = "buffer", "save_stdout", "save_stderr"

    def __init__(self):
        self.buffer = io.StringIO()

    def __enter__(self):
        sys.stdout.flush()
        sys.stderr.flush()
        self.save_stdout = sys.stdout
        self.save_stderr = sys.stderr
        buffer = self.buffer
        buffer.seek(0)
        buffer.truncate()
        sys.stdout = buffer
        sys.stderr = buffer

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.save_stdout
        sys.stderr = self.save_stderr

    def value(self):
        return self.buffer.getvalue()


def _exception_to_str(ex:BaseException) -> str:
    return f"{ex.__class__.__name__}: {ex}"


def _print_mismatch_text(text:str, mismatch_lineno:int):
    for lineno, line in enumerate(textwrap.dedent(text).splitlines()):
        print("--> " if lineno == mismatch_lineno else
              "    ", end='')
        print(line)
    if mismatch_lineno == -1:
        print("--> [end]")


def _run(cases:list[_Case], failstop:bool):

    print()
    print(f"Running {len(cases)} tests")
    print()

    namewd = 2 + max(len(case[0]) for case in cases)
    correct = 0
    captured_output = _CapturedOutput()

    for name, fn in cases:
        print("    " + name.ljust(namewd,'.'),end='',flush=True)
        try:
            with captured_output:
                fn()
            print("OK")
            correct += 1
        except BaseException as failure:
            print("FAILED")
            print()
            if (docstr := inspect.getdoc(fn)):
                print("Test Description:")
                print()
                print(textwrap.indent(docstr.rstrip(),"    "))
                print()
            if (output := captured_output.value()):
                print("Test Output:")
                print()
                print(textwrap.indent(output.rstrip(),"    "))
                print()
            if isinstance(failure,DotMismatch):
                print("Expected DOT:")
                print()
                _print_mismatch_text(failure.expected, failure.expected_lineno)
                print()
                print("Actual DOT:")
                print()
                _print_mismatch_text(failure.actual, failure.actual_lineno)
                print()
            else:
                print("Test Exception:")
                print()
                print(f"    {_exception_to_str(failure)}")
                print()
            for frame in traceback.format_tb(failure.__traceback__)[1:]:
                print(textwrap.indent(frame.rstrip(),"    "))
            cause = failure.__cause__
            while cause is not None:
                print()
                print("Caused By:")
                print()
                print(f"    {_exception_to_str(cause)}")
                print()
                for frame in traceback.format_tb(cause.__traceback__)[1:]:
                    print(textwrap.indent(frame.rstrip(),"    "))
                cause = cause.__cause__
            print()
            if failstop:
                sys.exit(1)

    print()
    print(f"{correct} out of {len(cases)} tests succeeded")
    print()

    if correct < len(cases):
        sys.exit(1)


def _main():

    parser = ArgumentParser(
        description="Test LiveImport")

    parser.add_argument("pattern", nargs='?', default=None,
        help="Only run tests with names containing this regex")

    parser.add_argument("-reverse", action="store_true",
        help="Run tests in reverse order")

    parser.add_argument("-failstop", action="store_true",
        help="Stop immediately on failure")

    args = parser.parse_args()

    cases = []
    cases.extend(_get_cases(core))
    cases.extend(_get_cases(identifiers))
    cases.extend(_get_cases(internals))
    cases.extend(_get_cases(render))
    cases.extend(_get_cases(show))
    cases.extend(_get_cases(styling))

    if (pattern := args.pattern) is not None:
        cases = [ case for case in cases
                  if re.search(pattern,case[0]) ]

    if args.reverse:
        cases = list(reversed(cases))

    with fakedots():
        _run(cases,args.failstop)


if __name__ == '__main__':
    _main()
