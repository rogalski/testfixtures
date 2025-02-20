import os
import sys
from tempfile import TemporaryFile

from testfixtures.comparison import compare
from testfixtures.compat import StringIO, Unicode


class OutputCapture(object):
    """
    A context manager for capturing output to the
    :attr:`sys.stdout` and :attr:`sys.stderr` streams.

    :param separate: If ``True``, ``stdout`` and ``stderr`` will be captured
                     separately and their expected values must be passed to
                     :meth:`~OutputCapture.compare`.

    :param fd: If ``True``, the underlying file descriptors will be captured,
               rather than just the attributes on :mod:`sys`. This allows
               you to capture things like subprocesses that write directly
               to the file descriptors, but is more invasive, so only use it
               when you need it.

    .. note:: If ``separate`` is passed as ``True``,
              :attr:`OutputCapture.captured` will be an empty string.
    """

    original_stdout = None
    original_stderr = None

    def __init__(self, separate=False, fd=False):
        self.separate = separate
        self.fd = fd

    def __enter__(self):
        if self.fd:
            self.output = TemporaryFile()
            self.stdout = TemporaryFile()
            self.stderr = TemporaryFile()
        else:
            self.output = StringIO()
            self.stdout = StringIO()
            self.stderr = StringIO()
        self.enable()
        return self

    def __exit__(self, *args):
        self.disable()

    def disable(self):
        "Disable the output capture if it is enabled."
        if self.fd:
            for original, current in (
                (self.original_stdout, sys.stdout),
                (self.original_stderr, sys.stderr),
            ):
                os.dup2(original, current.fileno())
                os.close(original)

        else:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr

    def enable(self):
        "Enable the output capture if it is disabled."
        if self.original_stdout is None:
            if self.fd:
                self.original_stdout = os.dup(sys.stdout.fileno())
                self.original_stderr = os.dup(sys.stderr.fileno())
            else:
                self.original_stdout = sys.stdout
                self.original_stderr = sys.stderr
        if self.separate:
            if self.fd:
                os.dup2(self.stdout.fileno(), sys.stdout.fileno())
                os.dup2(self.stderr.fileno(), sys.stderr.fileno())
            else:
                sys.stdout = self.stdout
                sys.stderr = self.stderr
        else:
            if self.fd:
                os.dup2(self.output.fileno(), sys.stdout.fileno())
                os.dup2(self.output.fileno(), sys.stderr.fileno())
            else:
                sys.stdout = sys.stderr = self.output

    def _read(self, stream):
        if self.fd:
            stream.seek(0)
            return stream.read()
        else:
            return stream.getvalue()


    @property
    def captured(self):
        "A property containing any output that has been captured so far."
        return self._read(self.output)

    def compare(self, expected=u'', stdout=u'', stderr=u''):
        """
        Compare the captured output to that expected. If the output is
        not the same, an :class:`AssertionError` will be raised.

        :param expected: A string containing the expected combined output
                         of ``stdout`` and ``stderr``.

        :param stdout: A string containing the expected output to ``stdout``.

        :param stderr: A string containing the expected output to ``stderr``.
        """
        for prefix, _expected, captured in (
                (None, expected, self.captured),
                ('stdout', stdout, self._read(self.stdout)),
                ('stderr', stderr, self._read(self.stderr)),
        ):
            if self.fd and isinstance(_expected, Unicode):
                _expected = _expected.encode()
            compare(_expected.strip(), actual=captured.strip(), prefix=prefix)
