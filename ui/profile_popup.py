import customtkinter as ctk
from ui.theme import APP_COLORS


class ProfileConnectPopup(ctk.CTkToplevel):
    def __init__(self, master, on_github, on_google, on_close=None):
        super().__init__(master)

        self.on_github = on_github
        self.on_google = on_google
        self.on_close = on_close

        self.title("Conectar conta")
        self.geometry("420x270")
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
            text="Escolha como deseja entrar no Automation Branch.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13),
            justify="left"
        ).pack(anchor="w", pady=(0, 18))

        github_btn = ctk.CTkButton(
            container,
            text="Continuar com GitHub",
            height=42,
            fg_color="#2563EB",
            hover_color="#3B82F6",
            text_color="#FFFFFF",
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_github
        )
        github_btn.pack(fill="x", pady=(0, 10))

        google_btn = ctk.CTkButton(
            container,
            text="Continuar com Google",
            height=42,
            fg_color="#374151",
            hover_color="#4B5563",
            text_color=APP_COLORS["text"],
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._handle_google
        )
        google_btn.pack(fill="x", pady=(0, 14))

        helper = ctk.CTkLabel(
            container,
            text="GitHub é o mais indicado para PR, branch e merge.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12)
        )
        helper.pack(anchor="w", pady=(0, 18))

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

    def _handle_google(self):
        if self.on_google:
            self.on_google()
        self.destroy()

    def _handle_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()