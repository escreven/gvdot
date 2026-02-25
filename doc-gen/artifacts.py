import re
import sys
import inspect
import textwrap
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import PurePath
from types import FunctionType
from gvdot import Dot

#
# Generate a rst code block string for the given text in the specified
# language.  The input lines are dedented, and any blank lines at the beginning
# or end are deleted.
#
# If language is "python", lines that look like
#
#   <whitespace>#+<anything>
#
# are included as
#
#   <whitespace><anything>
#
# and lines that end with #-<whitespace> as well as a last line like
# <whitespace>return<anything> are excluded.
#

def _code_block(language:str, text:str):

    text  = textwrap.dedent(text)
    lines = text.splitlines()

    while lines and re.fullmatch(r"\s*", lines[0]):
        del lines[0]

    while lines and re.fullmatch(r"\s*", lines[-1]):
        del lines[-1]

    if language == 'python':
        if lines and re.fullmatch(r"\s*return.*",lines[-1]):
            del lines[-1]
        transformed = []
        for line in lines:
            if match := re.fullmatch(r"(\s*)#\+\s*(.*)", line):
                transformed.append(match[1] + match[2])
            elif not re.fullmatch(r".*#-\s*", line):
                transformed.append(line)
        lines = transformed

    assert lines

    return f".. code-block:: {language}\n\n" + "".join(
        "    " + line + "\n" for line in lines)


#
# Examples can have images, python source code, and dot source code, all of
# which is optional.  save_artifacts() generates these artifacts and stores
# them in doc/_static.
#
# NOTE: This module must be in a directory at the repo root, so that
# ${__FILE__}/../doc/_static and ${__FILE__}/../doc/_code are the target image
# and code snippet directories.
#

@dataclass
class Artifact:
    name : str

    @abstractmethod
    def save(self, dir:PurePath):
        ...

@dataclass
class Image(Artifact):
    dot : Dot

    def save(self, dir:PurePath):
        name = self.name
        dot = self.dot
        dot.save(dir / f"_static/{name}.svg")

@dataclass
class DotCode(Artifact):
    dot : Dot

    def save(self, dir:PurePath):
        with open(dir / f"_code/{self.name}.dot.rst", "w") as f:
            print(_code_block("graphviz",str(self.dot)), file=f, end="")

@dataclass
class PythonCode(Artifact):
    code : FunctionType | str

    def save(self, dir:PurePath):

        if type(code := self.code) is str:
            source = code
        else:
            source = inspect.getsource(code) #type:ignore
            match = re.fullmatch(r"[ \t]*def [^\n]*\):[^\n]*\n(.*)",
                                 source, re.DOTALL)
            if not match:
                print(f"Unexpected source for {self.code}")
                sys.exit(1)
            source = match[1]

        with open(dir / f"_code/{self.name}.py.rst", "w") as f:
            print(_code_block("python",source), file=f, end="")


def save_artifacts(artifacts:list[Artifact]):

    dir = PurePath(__file__).parent.parent.joinpath("doc")

    for artifact in artifacts:
        artifact.save(dir)
