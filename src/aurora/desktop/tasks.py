"""Thread-safe background reads with main-thread Qt delivery."""

import queue
import threading
import uuid
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Slot

from aurora.jobs import Cancelled


class ReadTask(QRunnable):
    def __init__(self, kind, function, mailbox):
        super().__init__()

        self.kind = kind
        self.token = uuid.uuid4().hex
        self.function = function
        self.mailbox = mailbox
        self.event = threading.Event()

    def cancel(self, *_):
        self.event.set()

    def check(self):
        if self.event.is_set():
            raise Cancelled("Read cancelled")

    def run(self):
        try:
            self.check()
            value = self.function(self.check)
            self.check()

            self.mailbox.put(
                ("result", self.kind, self.token, value)
            )

        except Cancelled:
            return

        except Exception as exc:
            if not self.event.is_set():
                self.mailbox.put(
                    ("error", self.kind, self.token, str(exc))
                )


class ReaderJobs(QObject):
    def __init__(self, owner, result, error):
        super().__init__(owner)

        self.current = {}
        self.mailbox = queue.Queue()
        self.result_callback = result
        self.error_callback: Callable[[str], None] = error

        self.timer = QTimer(self)
        self.timer.setInterval(15)
        self.timer.timeout.connect(self.drain)

        owner.destroyed.connect(self.cancel_all)

    def busy(self, kind):
        return kind in self.current

    def start(self, kind, function):
        if kind in self.current:
            self.current[kind].cancel()

        task = ReadTask(kind, function, self.mailbox)
        self.current[kind] = task

        pool = QThreadPool.globalInstance()

        if pool.maxThreadCount() > 4:
            pool.setMaxThreadCount(4)

        self.timer.start()
        pool.start(task)

    @Slot()
    def drain(self):
        while True:
            try:
                status, kind, token, value = self.mailbox.get_nowait()
            except queue.Empty:
                break

            if status == "result":
                self.accept((kind, token, value))
            else:
                self.reject((kind, token, value))

        if not self.current:
            self.timer.stop()

    @Slot(object)
    def accept(self, payload):
        kind, token, value = payload
        task = self.current.get(kind)

        if task is not None and task.token == token:
            del self.current[kind]

            try:
                self.result_callback(kind, value)
            except Exception as exc:
                self.error_callback(str(exc))

    @Slot(object)
    def reject(self, payload):
        kind, token, error = payload
        task = self.current.get(kind)

        if task is not None and task.token == token:
            del self.current[kind]
            self.error_callback(error)

    @Slot()
    def cancel_all(self, *_):
        current = getattr(self, "current", None)
        if current is None:
            return

        for task in list(current.values()):
            task.cancel()

        current.clear()
