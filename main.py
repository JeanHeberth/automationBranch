import sys

from dotenv import load_dotenv

load_dotenv()


def _report_startup_error(exc: BaseException) -> None:
    message = (
        "Não foi possível iniciar o Automation Branch.\n\n"
        f"{type(exc).__name__}: {exc}"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro ao iniciar", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def main():
    try:
        from ui.main_window import MainWindow
    except ModuleNotFoundError as exc:
        if exc.name in {"_tkinter", "tkinter"}:
            raise SystemExit(
                "Tkinter não está disponível no Python atual.\n"
                "No macOS com Homebrew, instale o suporte (ajuste a versão do Python):\n"
                "  brew install python-tk\n"
                "Depois, recrie/ative o ambiente virtual e execute o projeto novamente."
            ) from exc
        raise

    try:
        app = MainWindow()
    except Exception as exc:
        _report_startup_error(exc)
        raise SystemExit(1) from exc

    app.mainloop()


if __name__ == "__main__":
    main()
