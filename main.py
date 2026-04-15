from ui.main_window import MainWindow
from dotenv import load_dotenv
load_dotenv()


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()