import webbrowser

import customtkinter as ctk

from ui.window_position import center_on_master

from ui.theme import APP_COLORS, load_icon


class DeviceLoginDialog(ctk.CTkToplevel):
    """Mostra o código do Device Flow do GitHub enquanto o app aguarda a autorização."""

    def __init__(self, master, user_code: str, verification_uri: str, on_cancel=None):
        super().__init__(master)

        self.user_code = user_code
        self.verification_uri = verification_uri
        self.on_cancel = on_cancel

        self.title("Autorizar no GitHub")
        self.geometry("440x325")
        self.resizable(False, False)
        self.configure(fg_color=APP_COLORS["panel"])
        self.transient(master)

        self._build_ui()
        self._center(master)

        self.protocol("WM_DELETE_WINDOW", self._handle_cancel)
        self.bind("<Escape>", lambda _e: self._handle_cancel())

        # grab/foco só depois de visível; sem isso a janela não recebe cliques no macOS.
        self.after(150, self._take_focus)

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color=APP_COLORS["panel"], corner_radius=12)
        container.pack(fill="both", expand=True, padx=18, pady=18)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(4, 10))

        ctk.CTkLabel(
            header, text="", image=load_icon("github.png", size=(26, 26), padding=0)
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            header,
            text="Autorizar no GitHub",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        ctk.CTkLabel(
            container,
            text=f"Abra {self.verification_uri.replace('https://', '')} e digite o código abaixo.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
            wraplength=380
        ).pack(fill="x", pady=(0, 12))

        code_box = ctk.CTkFrame(container, fg_color="#0b1220", corner_radius=10)
        code_box.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            code_box,
            text=self.user_code,
            text_color=APP_COLORS["accent"],
            font=ctk.CTkFont(family="Menlo", size=30, weight="bold")
        ).pack(pady=16)

        buttons = ctk.CTkFrame(container, fg_color="transparent")
        buttons.pack(fill="x", pady=(0, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)

        self.copy_btn = ctk.CTkButton(
            buttons,
            text="Copiar código",
            height=38,
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._copy_code
        )
        self.copy_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkButton(
            buttons,
            text="Abrir GitHub",
            height=38,
            fg_color="#24292F",
            hover_color="#32383F",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_browser
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ctk.CTkLabel(
            container,
            text="Aguardando a autorização no navegador...",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(0, 12))

        ctk.CTkButton(
            container,
            text="Cancelar",
            height=36,
            fg_color="transparent",
            hover_color="#1F2937",
            text_color=APP_COLORS["text"],
            border_width=1,
            border_color=APP_COLORS["border"],
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_cancel
        ).pack(fill="x")

    def _center(self, master):
        center_on_master(self, master)

    def _take_focus(self):
        if not self.winfo_exists():
            return
        self.lift()
        self.focus_force()

    def open_browser(self):
        webbrowser.open(self.verification_uri)

    def _copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.user_code)
        self.copy_btn.configure(text="Copiado ✓")

    def _handle_cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.close()

    def close(self):
        if self.winfo_exists():
            self.destroy()
