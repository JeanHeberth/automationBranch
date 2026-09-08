from dotenv import load_dotenv

load_dotenv()


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

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
