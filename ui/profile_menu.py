import customtkinter as ctk
from ui.theme import APP_COLORS


MENU_WIDTH = 280
SCREEN_MARGIN = 8


class ProfileMenu(ctk.CTkToplevel):
    def __init__(self, master, anchor_widget, session_data: dict, on_connect, on_logout):
        super().__init__(master)

        self.anchor_widget = anchor_widget
        self.session_data = session_data
        self.on_connect = on_connect
        self.on_logout = on_logout

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#111827")

        self._build_ui()
        self._place_near_anchor()

        self.bind("<FocusOut>", lambda _e: self._safe_close())
        self.focus_force()

    def _build_ui(self):
        container = ctk.CTkFrame(
            self,
            fg_color="#111827",
            corner_radius=12,
            border_width=1,
            border_color=APP_COLORS["border"]
        )
        container.pack(fill="both", expand=True, padx=1, pady=1)

        # Espaçador que fixa a largura do menu (escala junto com os demais widgets).
        ctk.CTkFrame(container, fg_color="transparent", width=MENU_WIDTH, height=0).pack()

        is_authenticated = self.session_data.get("is_authenticated", False)

        if is_authenticated:
            name = self.session_data.get("display_name") or "Usuário"
            provider = self.session_data.get("provider") or "Conta"
            email = self.session_data.get("email") or ""

            ctk.CTkLabel(
                container,
                text=name,
                text_color=APP_COLORS["text"],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            ).pack(fill="x", padx=12, pady=(12, 2))

            ctk.CTkLabel(
                container,
                text=f"{provider} conectado",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=12),
                anchor="w"
            ).pack(fill="x", padx=12)

            if email:
                ctk.CTkLabel(
                    container,
                    text=email,
                    text_color=APP_COLORS["muted"],
                    font=ctk.CTkFont(size=11),
                    anchor="w"
                ).pack(fill="x", padx=12, pady=(2, 8))

            divider = ctk.CTkFrame(container, fg_color=APP_COLORS["border"], height=1)
            divider.pack(fill="x", padx=10, pady=6)

            logout_btn = ctk.CTkButton(
                container,
                text="Desconectar",
                height=34,
                fg_color="transparent",
                hover_color="#374151",
                text_color=APP_COLORS["text"],
                anchor="w",
                corner_radius=8,
                command=self._handle_logout
            )
            logout_btn.pack(fill="x", padx=8, pady=(0, 8))
        else:
            ctk.CTkLabel(
                container,
                text="Nenhuma conta conectada",
                text_color=APP_COLORS["text"],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            ).pack(fill="x", padx=12, pady=(12, 4))

            ctk.CTkLabel(
                container,
                text="Conecte sua conta para usar recursos de PR e merge.",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=12),
                anchor="w",
                justify="left",
                wraplength=MENU_WIDTH - 40
            ).pack(fill="x", padx=12, pady=(0, 10))

            connect_btn = ctk.CTkButton(
                container,
                text="Conectar conta",
                height=36,
                fg_color="#2563EB",
                hover_color="#3B82F6",
                text_color="#FFFFFF",
                corner_radius=8,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=self._handle_connect
            )
            connect_btn.pack(fill="x", padx=10, pady=(0, 10))

    def _place_near_anchor(self):
        self.update_idletasks()

        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        # O botão de perfil fica no canto direito da janela: alinha a borda direita do menu
        # com a do botão (cresce para a esquerda) e garante que nada saia da tela.
        anchor_right = self.anchor_widget.winfo_rootx() + self.anchor_widget.winfo_width()
        x = anchor_right - width
        y = self.anchor_widget.winfo_rooty() + self.anchor_widget.winfo_height() + 6

        x = max(SCREEN_MARGIN, min(x, self.winfo_screenwidth() - width - SCREEN_MARGIN))
        y = max(SCREEN_MARGIN, min(y, self.winfo_screenheight() - height - SCREEN_MARGIN))

        self.geometry(f"+{x}+{y}")

    def _handle_connect(self):
        self._safe_close()
        if self.on_connect:
            self.on_connect()

    def _handle_logout(self):
        self._safe_close()
        if self.on_logout:
            self.on_logout()

    def _safe_close(self):
        if self.winfo_exists():
            self.destroy()