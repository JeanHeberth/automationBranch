import customtkinter as ctk

from services.protected_branches_service import matches_any
from ui.theme import APP_COLORS
from ui.window_position import center_on_master

EXAMPLE = "staging\nrelease/*\nhotfix/*"


class ProtectedBranchesDialog(ctk.CTkToplevel):
    """Edita as branches protegidas extras de um repositório.

    `defaults` são as sempre protegidas (só exibidas); `extras` é o que o repositório acrescenta.
    `get_result()` devolve a lista de linhas digitadas, ou None se cancelou.
    """

    def __init__(self, master, repo_name: str, defaults: list[str], extras: list[str]):
        super().__init__(master)
        self.withdraw()  # exibida só depois de posicionada (ver center_on_master)

        self.defaults = list(defaults)
        self.result: list[str] | None = None

        self.title("Branches protegidas")
        # Em telas menores, 680px estoura a altura útil (desconta barra de título e Dock).
        height = min(680, max(self.winfo_screenheight() - 220, 560))
        self.geometry(f"520x{height}")
        self.minsize(520, 520)
        self.resizable(False, True)
        self.configure(fg_color=APP_COLORS["panel"])
        self.transient(master)

        self._build_ui(repo_name, extras)
        center_on_master(self, master)
        self.after(150, self._take_focus)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self, repo_name: str, extras: list[str]):
        box = ctk.CTkFrame(self, fg_color=APP_COLORS["panel"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            box, text="Branches protegidas", text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=20, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(4, 2))

        ctk.CTkLabel(
            box, text=f"Repositório: {repo_name}", text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12), anchor="w",
        ).pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            box,
            text="Uma branch protegida não pode ser deletada, renomeada, nem ter o histórico "
                 "reescrito (amend, rebase, reset) por este app.",
            text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=12),
            justify="left", anchor="w", wraplength=440,
        ).pack(fill="x", pady=(0, 14))

        # Botões primeiro (side="bottom") para nunca serem cortados quando a janela é curta.
        actions = ctk.CTkFrame(box, fg_color="transparent")
        actions.pack(fill="x", side="bottom", pady=(12, 0))

        ctk.CTkButton(
            actions, text="Cancelar", width=100, height=36, fg_color="transparent",
            hover_color="#1F2937", text_color=APP_COLORS["text"], border_width=1,
            border_color=APP_COLORS["border"], command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            actions, text="Salvar", width=110, height=36, font=ctk.CTkFont(weight="bold"),
            command=self._confirm,
        ).pack(side="right")
        ctk.CTkButton(
            actions, text="Restaurar padrão", width=130, height=36, fg_color="transparent",
            hover_color="#1F2937", text_color=APP_COLORS["text"], border_width=1,
            border_color=APP_COLORS["border"], command=self._restore_defaults,
        ).pack(side="right", padx=(0, 8))

        # --- sempre protegidas ---
        ctk.CTkLabel(
            box, text="Sempre protegidas (não editável)", text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(0, 6))

        chips = ctk.CTkFrame(box, fg_color="transparent")
        chips.pack(fill="x", pady=(0, 14))
        for name in self.defaults:
            ctk.CTkLabel(
                chips, text=name, text_color=APP_COLORS["text"], fg_color="#1F2937",
                corner_radius=8, font=ctk.CTkFont(size=12), padx=10, pady=3,
            ).pack(side="left", padx=(0, 6))

        # --- extras ---
        ctk.CTkLabel(
            box, text="Outras branches a proteger", text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(
            box,
            text="Um nome ou padrão por linha. O * vale por qualquer trecho: "
                 "release/* protege release/1.0, release/2.0…",
            text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=12),
            justify="left", anchor="w", wraplength=440,
        ).pack(fill="x", pady=(0, 6))

        self._textbox = ctk.CTkTextbox(
            box, height=110, fg_color="#1b1f27", border_width=1, border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"], font=ctk.CTkFont(size=13),
        )
        self._textbox.pack(fill="both", expand=True)
        if extras:
            self._textbox.insert("1.0", "\n".join(extras))
        self._textbox.bind("<KeyRelease>", lambda _e: self._update_test_result())

        example = ctk.CTkFrame(box, fg_color="#1b2430", corner_radius=10)
        example.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(
            example, text="Exemplo de preenchimento:", text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=11), anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(
            example, text=EXAMPLE, text_color=APP_COLORS["text"],
            font=ctk.CTkFont(family="Menlo", size=12), justify="left", anchor="w",
        ).pack(fill="x", padx=10, pady=(2, 8))

        # --- testar um nome ---
        ctk.CTkLabel(
            box, text="Testar uma branch", text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(fill="x", pady=(14, 6))

        self._test_entry = ctk.CTkEntry(
            box, placeholder_text="ex.: release/1.0", height=34, fg_color="#1b1f27",
            border_color=APP_COLORS["border"], text_color=APP_COLORS["text"],
        )
        self._test_entry.pack(fill="x")
        self._test_entry.bind("<KeyRelease>", lambda _e: self._update_test_result())

        self._test_label = ctk.CTkLabel(
            box, text="", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=12), anchor="w",
        )
        self._test_label.pack(fill="x", pady=(4, 0))

    def _typed_patterns(self) -> list[str]:
        text = self._textbox.get("1.0", "end")
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _update_test_result(self):
        name = self._test_entry.get().strip()
        if not name:
            self._test_label.configure(text="", text_color=APP_COLORS["muted"])
        elif matches_any(name, [*self.defaults, *self._typed_patterns()]):
            self._test_label.configure(text=f"'{name}' fica protegida.", text_color=APP_COLORS["warning"])
        else:
            self._test_label.configure(text=f"'{name}' não é protegida.", text_color=APP_COLORS["success"])

    def _restore_defaults(self):
        self._textbox.delete("1.0", "end")
        self._update_test_result()

    def _take_focus(self):
        self.lift()
        self.grab_set()
        self.focus_force()
        self._textbox.focus_set()

    def _confirm(self):
        self.result = self._typed_patterns()
        self.destroy()

    def get_result(self) -> list[str] | None:
        self.master.wait_window(self)
        return self.result
