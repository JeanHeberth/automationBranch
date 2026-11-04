import customtkinter as ctk

from ui.actions_menu import COLUMNS, MENU_SPEC, OPERATION_NAMES
from ui.theme import APP_COLORS, load_icon

PANEL_BG = "#111827"
ROW_HOVER = "#1f2937"
COLUMN_WIDTH = 250
ROW_HEIGHT = 32
SCREEN_MARGIN = 8


class ActionsPanel(ctk.CTkToplevel):
    """Painel flutuante com todas as ações agrupadas, no tema do app (substitui o menu nativo).

    Abre ancorado no botão, com a borda direita alinhada à dele. Fecha ao escolher uma ação,
    com Esc ou ao perder o foco. Com uma operação parada em conflito, mostra no topo
    Continuar e Abortar.
    """

    def __init__(self, master, anchor_widget, handlers: dict, operation: str | None = None, on_close=None):
        super().__init__(master)

        self.handlers = handlers
        self.operation = operation
        self.on_close = on_close
        self._closed = False

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=PANEL_BG)

        self._build_ui()
        self._place(anchor_widget)

        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<FocusOut>", self._on_focus_out)
        self.focus_force()

    # ---------- construção ----------

    def _build_ui(self):
        frame = ctk.CTkFrame(
            self, fg_color=PANEL_BG, corner_radius=12, border_width=1, border_color=APP_COLORS["border"]
        )
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        if self.operation:
            self._build_operation_banner(frame)

        columns = ctk.CTkFrame(frame, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=8, pady=8)

        for column_index, group_indexes in enumerate(COLUMNS):
            column = ctk.CTkFrame(columns, fg_color="transparent", width=COLUMN_WIDTH)
            column.grid(row=0, column=column_index, sticky="nsew", padx=4)
            for group_index in group_indexes:
                self._build_group(column, *MENU_SPEC[group_index])

    def _build_operation_banner(self, frame):
        name = OPERATION_NAMES.get(self.operation, self.operation)

        banner = ctk.CTkFrame(frame, fg_color="#3b2f0b", corner_radius=8, border_width=1, border_color=APP_COLORS["warning"])
        banner.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(
            banner,
            text=f"{name.capitalize()} em andamento. Resolva os conflitos, coloque os arquivos em stage e continue.",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=2 * COLUMN_WIDTH - 10,
        ).pack(fill="x", padx=10, pady=(8, 6))

        buttons = ctk.CTkFrame(banner, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(
            buttons, text=f"Continuar {name}", height=30, corner_radius=8,
            fg_color=APP_COLORS["accent"], hover_color="#2563eb", text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self._choose("continue"),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            buttons, text=f"Abortar {name}", height=30, corner_radius=8,
            fg_color="transparent", hover_color="#7f1d1d", text_color=APP_COLORS["danger"],
            border_width=1, border_color=APP_COLORS["danger"],
            font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self._choose("abort"),
        ).pack(side="left")

    def _build_group(self, column, title: str, items: list):
        ctk.CTkLabel(
            column,
            text=title.upper(),
            anchor="w",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(fill="x", padx=8, pady=(8, 2))

        for label, key, icon in items:
            self._add_item(column, label, key, icon)

    def _add_item(self, column, label: str, key: str, icon: str):
        row = ctk.CTkFrame(column, fg_color="transparent", corner_radius=6, height=ROW_HEIGHT, cursor="hand2")
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        image = ctk.CTkLabel(row, text="", image=load_icon(icon, size=(16, 16), padding=0), width=20)
        image.pack(side="left", padx=(8, 8))

        text = ctk.CTkLabel(
            row, text=label, anchor="w", text_color=APP_COLORS["text"], font=ctk.CTkFont(size=12)
        )
        text.pack(side="left", fill="x", expand=True)

        for widget in (row, image, text):
            widget.bind("<Button-1>", lambda _e, k=key: self._choose(k))
            widget.bind("<Enter>", lambda _e, r=row: r.configure(fg_color=ROW_HOVER))
            widget.bind("<Leave>", lambda _e, r=row: r.configure(fg_color="transparent"))

    # ---------- posição e foco ----------

    def _place(self, anchor_widget):
        self.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()

        # O botão fica no canto direito da janela: alinha a borda direita do painel com a dele.
        x = anchor_widget.winfo_rootx() + anchor_widget.winfo_width() - width
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 6

        x = max(SCREEN_MARGIN, min(x, self.winfo_screenwidth() - width - SCREEN_MARGIN))
        y = max(SCREEN_MARGIN, min(y, self.winfo_screenheight() - height - SCREEN_MARGIN))
        self.geometry(f"+{x}+{y}")

    def _on_focus_out(self, _event=None):
        # Depois que o foco assenta: mover o foco entre widgets do próprio painel não fecha.
        self.after(60, self._close_if_unfocused)

    def _close_if_unfocused(self):
        if self.winfo_exists() and self.focus_displayof() is None:
            self.close()

    # ---------- ações ----------

    def _choose(self, key: str):
        handler = self.handlers[key]
        self.close()
        self.master.after(10, handler)  # depois de fechar: o handler abre diálogos e tarefas

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.on_close:
            self.on_close()
        if self.winfo_exists():
            self.destroy()
