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


class _TextDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, prompt: str, initialvalue: str = ""):
        super().__init__(master)
        self.result: str | None = None

        self.title(title)
        self.geometry("460x320")
        self.resizable(False, False)
        self.transient(master)

        ctk.CTkLabel(self, text=prompt, anchor="w").pack(fill="x", padx=18, pady=(18, 6))

        self._textbox = ctk.CTkTextbox(self, wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        if initialvalue:
            self._textbox.insert("1.0", initialvalue)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(buttons, text="Cancelar", width=100, command=self.destroy).pack(side="right")
        ctk.CTkButton(buttons, text="OK", width=100, command=self._confirm).pack(side="right", padx=(0, 8))

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        # grab/foco após a janela estar visível; sem isso o campo fica bloqueado no macOS.
        self.after(150, self._take_focus)

    def _take_focus(self):
        self.lift()
        self.grab_set()
        self.focus_force()
        self._textbox.focus_set()

    def _confirm(self):
        self.result = self._textbox.get("1.0", "end").strip()
        self.destroy()


def ask_text(master, title: str, prompt: str, initialvalue: str = "") -> str | None:
    """Diálogo com caixa de texto multilinha. Retorna None se cancelado."""
    dialog = _TextDialog(master, title, prompt, initialvalue)
    master.wait_window(dialog)
    return dialog.result
