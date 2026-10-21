"""Instrumentação de performance, desligada por padrão.

Ative com a variável de ambiente AUTOMATION_PERF=1. As medições vão para
`automation_perf.log` (na pasta atual) e para o stderr. Serve para descobrir, no
Windows, onde o tempo vai: processos git, montagem de widgets ou travamentos da UI.
"""
import os
import threading
import time
from contextlib import contextmanager

ENABLED = os.getenv("AUTOMATION_PERF", "").strip().lower() in {"1", "true", "yes", "on"}
LOG_PATH = os.getenv("AUTOMATION_PERF_LOG", "automation_perf.log")

_lock = threading.Lock()
_START = time.perf_counter()


def _thread_tag() -> str:
    return "UI" if threading.current_thread() is threading.main_thread() else "bg"


def log(message: str) -> None:
    if not ENABLED:
        return
    line = f"[{time.perf_counter() - _START:9.3f}s] [{_thread_tag():>2}] {message}"
    with _lock:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass
        print(line, flush=True)


@contextmanager
def timed(label: str):
    """Mede o bloco e registra a duração (custo zero quando desligado)."""
    if not ENABLED:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        log(f"{(time.perf_counter() - start) * 1000:8.1f} ms  {label}")


def start_ui_lag_monitor(widget, interval_ms: int = 50, threshold_ms: int = 150) -> None:
    """Detecta travamentos da UI: se o loop do Tk atrasa mais que o limite, registra o atraso."""
    if not ENABLED:
        return

    state = {"last": time.perf_counter()}

    def tick():
        now = time.perf_counter()
        lag = (now - state["last"]) * 1000 - interval_ms
        if lag > threshold_ms:
            log(f"{lag:8.1f} ms  *** UI TRAVADA (loop do Tk atrasou) ***")
        state["last"] = now
        try:
            widget.after(interval_ms, tick)
        except Exception:
            pass

    widget.after(interval_ms, tick)
    log("monitor de travamento da UI iniciado")
