"""Cooperative read jobs; all widget callbacks are dispatched on the Qt UI thread."""
import threading
import uuid
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from aurora.jobs import Cancelled


class Signals(QObject):
    result = Signal(object)
    error = Signal(object)


class ReadTask(QRunnable):
    def __init__(self, kind, function):
        super().__init__(); self.kind = kind; self.token = uuid.uuid4().hex
        self.function = function; self.signals = Signals(); self.event = threading.Event()

    def cancel(self, *_): self.event.set()
    def check(self):
        if self.event.is_set(): raise Cancelled('Read cancelled')

    def run(self):
        try:
            self.check(); value = self.function(self.check); self.check()
            self.deliver(self.signals.result, (self.kind, self.token, value))
        except Cancelled:
            return
        except Exception as exc:
            self.deliver(self.signals.error, (self.kind, self.token, str(exc)))

    def deliver(self, signal, payload):
        if self.event.is_set(): return
        try: signal.emit(payload)
        except RuntimeError as exc:
            # The application may have destroyed its QObject signal sources at shutdown.
            if 'deleted' not in str(exc): raise


class ReaderJobs(QObject):
    def __init__(self, owner, result, error):
        super().__init__(owner); self.current = {}; self.result_callback = result; self.error_callback = error
        owner.destroyed.connect(self.cancel_all)

    def busy(self, kind): return kind in self.current

    def start(self, kind, function):
        if kind in self.current: self.current[kind].cancel()
        task = ReadTask(kind, function); self.current[kind] = task
        task.signals.result.connect(self.accept)
        task.signals.error.connect(self.reject)
        pool = QThreadPool.globalInstance()
        if pool.maxThreadCount() > 4: pool.setMaxThreadCount(4)
        pool.start(task)

    @Slot(object)
    def accept(self, payload):
        kind, token, value = payload
        task = self.current.get(kind)
        if task is not None and task.token == token:
            del self.current[kind]
            try: self.result_callback(kind, value)
            except Exception as exc: self.error_callback(str(exc))

    @Slot(object)
    def reject(self, payload):
        kind, token, error = payload
        task = self.current.get(kind)
        if task is not None and task.token == token:
            del self.current[kind]; self.error_callback(error)

    @Slot()
    def cancel_all(self, *_):
        for task in self.current.values(): task.cancel()
        self.current.clear()
