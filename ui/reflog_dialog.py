import customtkinter as ctk

from ui.window_position import center_on_master

from ui.theme import APP_COLORS

ROW_BG = "#2a2f3a"
SELECTED_BG = "#1d4ed8"


class ReflogDialog(ctk.CTkToplevel):
    """Histórico do HEAD (git reflog): rede de segurança para voltar a um ponto anterior."""

    def __init__(self, master, entries: list[dict], on_view, on_branch, on_reset):
        super().__init__(master)

        self.entries = entries
        self.on_view = on_view
        self.on_branch = on_branch
        self.on_reset = on_reset
        self._selected: dict | None = None
        self._rows: list[tuple[dict, ctk.CTkFrame]] = []

        self.title("Reflog")
        self.geometry("680x520")
        self.minsize(520, 360)
        self.configure(fg_color=APP_COLORS["panel"])
        self.transient(master)

        self._build_ui()
        self._center(master)
        self.bind("<Escape>", lambda _e: self.close())
        self.after(150, self._take_focus)

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text="Histórico do HEAD",
            anchor="w",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(fill="x", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            self,
            text="Tudo o que moveu o HEAD, inclusive commits que saíram da branch. Escolha um ponto.",
            anchor="w",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).pack(fill="x", padx=16, pady=(0, 8))

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        if not self.entries:
            ctk.CTkLabel(self.list_frame, text="Reflog vazio.", text_color=APP_COLORS["muted"]).pack(pady=30)

        for entry in self.entries:
            self._add_row(entry)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        buttons.grid_columnconfigure((0, 1, 2), weight=1)

        self.view_btn = self._button(buttons, "Ver commit", "#334155", "#475569", 0, self._view)
        self.branch_btn = self._button(buttons, "Criar branch aqui…", "#334155", "#475569", 1, self._branch)
        self.reset_btn = self._button(buttons, "Voltar a este ponto", "#7f1d1d", "#991b1b", 2, self._reset)
        self._set_buttons_enabled(False)

    @staticmethod
    def _button(parent, text, color, hover, column, command):
        button = ctk.CTkButton(
            parent, text=text, height=36, fg_color=color, hover_color=hover, corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"), command=command,
        )
        button.grid(row=0, column=column, sticky="ew", padx=3)
        return button

    def _add_row(self, entry: dict):
        row = ctk.CTkFrame(self.list_frame, fg_color=ROW_BG, corner_radius=8, cursor="hand2")
        row.pack(fill="x", padx=4, pady=2)

        title = ctk.CTkLabel(
            row,
            text=f"{entry['selector']}   {entry['hash']}   {entry['message']}",
            anchor="w",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        title.pack(fill="x", padx=10, pady=(6, 0))

        subtitle = ctk.CTkLabel(
            row, text=entry["date"], anchor="w", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=11)
        )
        subtitle.pack(fill="x", padx=10, pady=(0, 6))

        for widget in (row, title, subtitle):
            widget.bind("<Button-1>", lambda _e, e=entry: self._select(e))

        self._rows.append((entry, row))

    def _select(self, entry: dict):
        self._selected = entry
        for candidate, row in self._rows:
            row.configure(fg_color=SELECTED_BG if candidate is entry else ROW_BG)
        self._set_buttons_enabled(True)

    def _set_buttons_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for button in (self.view_btn, self.branch_btn, self.reset_btn):
            button.configure(state=state)

    def _view(self):
        if self._selected:
            self.on_view(self._selected)

    def _branch(self):
        if self._selected:
            self.on_branch(self._selected)

    def _reset(self):
        if self._selected:
            self.on_reset(self._selected)

    def _center(self, master):
        center_on_master(self, master, top_offset=60)

    def _take_focus(self):
        if self.winfo_exists():
            self.lift()
            self.focus_force()

    def close(self):
        if self.winfo_exists():
            self.destroy()
