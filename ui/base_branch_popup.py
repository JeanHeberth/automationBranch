import customtkinter as ctk

from ui.window_position import center_on_master
from ui.theme import APP_COLORS


class BaseBranchPopup(ctk.CTkToplevel):
    """Select modal para escolher uma branch (base do PR por padrão; serve também para merge,
    rebase e limpeza de branches)."""

    def __init__(
        self,
        master,
        options: list[str],
        title: str = "Abrir Pull Request",
        label: str = "Branch base do PR",
        confirm_text: str = "Continuar",
    ):
        super().__init__(master)
        self.withdraw()  # exibida só depois de posicionada (ver center_on_master)

        self.options = options
        self._label = label
        self._confirm_text = confirm_text
        self.selection: str | None = None
        self.branch_var = ctk.StringVar(value=options[0] if options else "")

        self.title(title)
        self.geometry("380x200")
        self.resizable(False, False)
        self.configure(fg_color=APP_COLORS["panel"])

        self.transient(master)
        self._build_ui()
        self._center(master)
        self.after(150, self.grab_set)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color=APP_COLORS["panel"], corner_radius=12)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            container,
            text=self._label,
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkOptionMenu(
            container,
            values=self.options or [""],
            variable=self.branch_var,
        ).pack(fill="x", pady=(0, 16))

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x", side="bottom")

        ctk.CTkButton(buttons, text="Cancelar", width=100, command=self.destroy).pack(side="right")
        ctk.CTkButton(buttons, text=self._confirm_text, width=100, command=self._confirm).pack(
            side="right", padx=(0, 8)
        )

    def _confirm(self):
        self.selection = self.branch_var.get() or None
        self.destroy()

    def _center(self, master):
        center_on_master(self, master)

    def get_selection(self) -> str | None:
        self.master.wait_window(self)
        return self.selection
