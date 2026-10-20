import customtkinter as ctk


class _PrefilledInputDialog(ctk.CTkInputDialog):
    def __init__(self, *args, initialvalue: str = "", **kwargs):
        self._initialvalue = initialvalue
        super().__init__(*args, **kwargs)

    def _create_widgets(self):
        super()._create_widgets()
        if self._initialvalue:
            self._entry.insert(0, self._initialvalue)


def ask_string(title: str, prompt: str, initialvalue: str = "") -> str | None:
    """Substitui tkinter.simpledialog.askstring.

    O simpledialog quebra no macOS com alguns builds do Tk
    (TclError: invalid command name "::tk::unsupported::MacWindowStyle").
    Retorna None se o usuário cancelar.
    """
    return _PrefilledInputDialog(
        title=title, text=prompt, initialvalue=initialvalue
    ).get_input()
