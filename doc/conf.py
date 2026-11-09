import sys
import os
sys.path.insert(0, os.path.abspath('../src'))

import re
from inspect import formatannotation
from gvdot import __version__

project = 'gvdot'
copyright = '2026, Edward Screven'
author = 'Edward Screven'

version = re.match(r"\d+\.\d+",__version__)[0]  #type:ignore
release = __version__

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
]

# No templates for now.
# templates_path = ['_templates']
html_static_path = ['_static']
html_css_files = ['css/custom.css']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'en'

html_theme = 'sphinx_rtd_theme'
html_show_sourcelink = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

add_module_names = False
autodoc_member_order = 'bysource'

def generic_class_signature(
    app, what, name, obj, options, signature, return_annotation
):
    if what != "class":
        return None

    params = obj.__dict__.get("__type_params__", ())
    if not params or signature is None:
        return None

    def format_param(p):
        param = (
            ("**" if type(p).__name__ == "ParamSpec"
             else "*" if type(p).__name__ == "TypeVarTuple"
             else "") + p.__name__
        )
        bound = getattr(p, "__bound__", None)
        constraints = getattr(p, "__constraints__", ())
        if bound is not None:
            param += ":" + formatannotation(
                bound, base_module=getattr(bound, "__module__", None)
            )
        elif constraints:
            param += ":(" + ", ".join(
                formatannotation(t, base_module=getattr(t, "__module__", None))
                for t in constraints
            ) + ")"
        return param

    type_params = ", ".join(format_param(p) for p in params)

    return f"[{type_params}]{signature}", return_annotation


def setup(app):
    app.connect("autodoc-process-signature", generic_class_signature)
