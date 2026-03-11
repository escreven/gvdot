from __future__ import annotations
import os
import time
import textwrap
from copy import deepcopy
from typing import Any
from jupyter_client import KernelManager  #type:ignore

#
# This module acts as a frontend to an IPython kernel running cells that are
# Dot.show() and Dot.show_source() tests.  Those tests are not exhaustive with
# respect to show() and show_source() behavior -- show.py takes care of that --
# but they do verify that expected show() and show_source() output is available
# through a notebook UI.
#
# We use a long timeout because GitHub Windows runners can be very slow,
# especially when launching Graphviz programs in a subprocess.
#

_TIMEOUT = 60.0

#
# Tracing is enabled when this module is run from the command line.
#

_trace_enable = False

def _trace(*s:str):
    if _trace_enable:
        print(" ".join(s))

def _trace_multiline(text:str):
    if _trace_enable:
        lines = text.splitlines()
        for line in lines:
            print(".... | " + line)

#
# Encapsulate an IPython kernel connection.
#

class _Kernel:

    __slots__ = "manager", "client", "counter"

    def __init__(self):
        """
        Create an IPython kernel having this module's source directory as its
        current working directory.
        """
        if '__file__' not in globals():
            raise RuntimeError("Bootstrap test requires __file__")

        dir = os.path.dirname(__file__)
        if not dir: dir = '.'

        self.manager = KernelManager(kernel_name='python3')
        self.manager.start_kernel(cwd=dir)

        self.client = self.manager.client()
        self.client.start_channels()
        self.client.wait_for_ready(timeout=_TIMEOUT)

        self.counter = 0

    def run_cell(self, code:str) -> tuple[
            dict[str,str]|None,  # display message data, if any
            dict[str,Any]|None   # error message content, if any
        ]:
        """
        Send code to the kernel, returning any display data and error message
        received.  `run_cell()` raises a `RuntimeError` if it receives more
        than one display_data message, more than one error message, or any
        stream data.
        """
        code = textwrap.dedent(code)

        #
        # Send the request.
        #

        _trace("-------------------------------------------------")
        _trace(f"Send {repr(code)}")

        client = self.client
        self.client.execute(code, silent=False,
                            store_history=True,
                            allow_stdin=False, stop_on_error=True)

        #
        # The kernel sends many messages in response
        #

        display:dict[str,str]|None = None
        error:dict[str,Any]|None = None

        while True:
            #
            # Wait for the next reply message.  Unfortunately, jupyter_client
            # fails with a non-public exception on timeout.
            #
            try:
                t0 = time.monotonic()
                msg = client.get_iopub_msg(timeout=_TIMEOUT)
                t1 = time.monotonic()
            except Exception as ex:
                raise RuntimeError(
                    "Message wait from kernel failed (timeout likely)") from ex

            #
            # Dispatch the message.  As a general matter, IPython cells can
            # generate multiple stream and display messages.  However, to
            # simplify the interface, we require cells to generate no stream
            # data (no writes to stdout/stderr), and no more than one display
            # data message (at most one call to display()).
            #

            mtype   = msg['msg_type']
            content = msg['content']

            _trace(f"Recv mtype={mtype} after {t1-t0:0.3f}s")

            if mtype == 'stream':
                name = content['name']
                text = content['text']
                _trace(f".... stream name={name}")
                _trace_multiline(text)
                lines = text.splitlines()
                while lines and not lines[0]:
                    del lines[0]
                line = lines[0] if lines else "(no data)"
                raise RuntimeError(f"Unexpected stream: {name}: {line}...")

            elif mtype == 'display_data':
                if display is not None:
                    raise RuntimeError("Multiple display messages for cell")
                data = content['data']
                for mimetype, text in data.items():
                    _trace(f".... {mimetype}")
                    _trace_multiline(text)
                display = deepcopy(data)

            elif mtype == 'error':
                if error is not None:
                    raise RuntimeError("Multiple error messages for cell")
                _trace(f".... ename={content['ename']}")
                _trace(f".... value={content['evalue']}")
                error = deepcopy(content)

            elif mtype == 'status':
                state = content['execution_state']
                _trace(f".... state={state}")
                if state == 'idle':
                    #
                    # The kernel is done.  It also sends a reply message on a
                    # different queue when finished; await that message.
                    #
                    client.get_shell_msg(timeout=_TIMEOUT)
                    break

        return display, error

    def close(self):
        """
        Shutdown the kernel.
        """
        #
        # We ignore failures here for two reasons.
        #    1. Anything that goes wrong here is not a gvdot issue, so the test
        #       should not fail.
        #    2. I have observed spurious jupyter_client errors during shutdown
        #       related to __del__ methods and GC.
        #
        try:
            self.client.stop_channels()
        except Exception:
            pass
        try:
            self.manager.shutdown_kernel(now=True)
        except Exception:
            pass


def _require_no_error(error:dict[str,Any]|None):
    if error is None: return
    ename = error['ename']
    evalue = error['evalue']
    raise AssertionError(f"Kernel exception {ename}: {evalue}")


def test_display():
    """
    When IPython is installed, methods show() and show_source() should display
    images and source through the frontend.  If show() cannot complete, it
    should display a markdown block and raise an exception visible through the
    frontend.
    """
    kernel = _Kernel()
    try:
        display, error = kernel.run_cell("""
        from gvdot import Dot
        dot = Dot().node("a").node("b").edge("a","b")
        """)

        _require_no_error(error)
        assert display is None

        display, error = kernel.run_cell("""
        dot.show()
        """)

        _require_no_error(error)
        assert display is not None and "image/svg+xml" in display

        display, error = kernel.run_cell("""
        dot.show_source()
        """)

        _require_no_error(error)
        assert (display is not None and "text/html" in display and
                "text/plain" in display and "a -- b" in display["text/plain"])

        display, error = kernel.run_cell("""
        dot.show(format="png")
        """)

        _require_no_error(error)
        assert display is not None and "image/png" in display

        display, error = kernel.run_cell("""
        dot.show(program="doesnotexist")
        """)

        assert error is not None and error['ename'] == 'ShowException'
        assert (display is not None and "text/markdown" in display and
                "doesnotexist" in display["text/markdown"])

    finally:
        kernel.close()


#
# frontend.py can be run from the command line.  That is useful for debugging
# frontend.py, and also tracing interaction with IPython kernels.
#
if __name__ == '__main__':
    _trace_enable = True
    test_display()
