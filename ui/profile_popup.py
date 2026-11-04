import customtkinter as ctk
from ui.theme import APP_COLORS, load_icon


class ProfileConnectPopup(ctk.CTkToplevel):
    def __init__(self, master, on_github, on_close=None):
        super().__init__(master)

        self.on_github = on_github
        self.on_close = on_close

        self.title("Conectar conta")
        self.geometry("440x270")
        self.resizable(False, False)
        self.configure(fg_color=APP_COLORS["panel"])

        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._center(master)

        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _build_ui(self):
        container = ctk.CTkFrame(
            self,
            fg_color=APP_COLORS["panel"],
            corner_radius=12
        )
        container.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            container,
            text="Conectar conta",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w", pady=(6, 8))

        ctk.CTkLabel(
            container,
            text="Entre com sua conta para usar os recursos do GitHub.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13),
            justify="left"
        ).pack(anchor="w", pady=(0, 18))

        self._provider_button(
            container,
            text="Continuar com GitHub",
            icon="github.png",
            fg_color="#24292F",
            hover_color="#32383F",
            text_color="#FFFFFF",
            command=self._handle_github,
        ).pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            container,
            text="Necessário para abrir e mesclar Pull Requests.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", pady=(0, 18))

        cancel_btn = ctk.CTkButton(
            container,
            text="Agora não",
            height=38,
            fg_color="transparent",
            hover_color="#1F2937",
            text_color=APP_COLORS["text"],
            border_width=1,
            border_color=APP_COLORS["border"],
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_close
        )
        cancel_btn.pack(fill="x")

    @staticmethod
    def _provider_button(parent, text, icon, fg_color, hover_color, text_color, command):
        """Botão de provedor: logo à esquerda e texto centralizado."""
        return ctk.CTkButton(
            parent,
            text=text,
            image=load_icon(icon, size=(20, 20), padding=0),
            compound="left",
            height=46,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            border_width=1,
            border_color=APP_COLORS["border"],
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=command
        )

    def _center(self, master):
        self.update_idletasks()

        width = self.winfo_width()
        height = self.winfo_height()

        master_x = master.winfo_rootx()
        master_y = master.winfo_rooty()
        master_width = master.winfo_width()
        master_height = master.winfo_height()

        x = master_x + (master_width - width) // 2
        y = master_y + (master_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _handle_github(self):
        if self.on_github:
            self.on_github()
        self.destroy()

    def _handle_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()