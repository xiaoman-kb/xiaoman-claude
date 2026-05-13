import os
import select
import sys
import termios
import threading
import tty


class TurnCancellation:
    def __init__(self):
        self._event = threading.Event()

    def reset(self):
        self._event.clear()

    def cancel(self):
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


class EscListener:
    def __init__(self, state: TurnCancellation):
        self.state = state
        self._thread = None
        self._stop = threading.Event()
        self._active = False
        self._started = False

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> bool:
        if self._started:
            return self._active
        if not sys.stdin.isatty():
            self._started = True
            self._active = False
            return False
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

    def _run(self):
        fd = sys.stdin.fileno()
        try:
            old = termios.tcgetattr(fd)
        except termios.error:
            self._active = False
            return
        self._active = True
        try:
            tty.setcbreak(fd)
            while not self._stop.is_set():
                ready, _, _ = select.select([fd], [], [], 0.1)
                if not ready:
                    continue
                data = os.read(fd, 1)
                if data == b"\x1b":
                    self.state.cancel()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            self._active = False
