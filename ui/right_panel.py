import customtkinter as ctk
from ui.theme import APP_COLORS


class RightPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0
        )

        self._build_header()
        self._build_file_list()
        self._build_commit_area()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=48)
        header.pack(fill="x", padx=10, pady=(8, 4))

        self.title = ctk.CTkLabel(
            header,
            text="Changes / Commit",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title.pack(side="left")

    def _build_file_list(self):
        self.files_container = ctk.CTkFrame(self, fg_color="transparent")
        self.files_container.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.files_title = ctk.CTkLabel(
            self.files_container,
            text="Arquivos",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.files_title.pack(anchor="w", padx=6, pady=(4, 6))

        self.scroll = ctk.CTkScrollableFrame(
            self.files_container,
            fg_color="transparent",
            height=260
        )
        self.scroll.pack(fill="both", expand=True)

    def _build_commit_area(self):
        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=10, pady=(4, 8))

        commit_container = ctk.CTkFrame(self, fg_color="transparent")
        commit_container.pack(fill="x", padx=10, pady=(0, 12))

        commit_title = ctk.CTkLabel(
            commit_container,
            text="Mensagem de commit",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        commit_title.pack(anchor="w", pady=(0, 6))

        self.commit_msg = ctk.CTkTextbox(
            commit_container,
            height=110,
            corner_radius=8,
            fg_color="#2a2f3a",
            text_color=APP_COLORS["text"],
            border_width=1,
            border_color=APP_COLORS["border"]
        )
        self.commit_msg.pack(fill="x", pady=(0, 10))
        self.commit_msg.insert("1.0", "Digite a mensagem do commit...")

        self.commit_btn = ctk.CTkButton(
            commit_container,
            text="Commit",
            height=38,
            fg_color=APP_COLORS["accent"],
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=8
        )
        self.commit_btn.pack(fill="x")

    def clear(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

    def set_files(self, files: list[str]):
        self.clear()

        if not files:
            self._empty_state("Nenhum arquivo encontrado.")
            return

        for file in files:
            self._create_file_item(file)

    def _create_file_item(self, text: str):
        item = ctk.CTkFrame(
            self.scroll,
            fg_color="#2a2f3a",
            corner_radius=8,
            height=40
        )
        item.pack(fill="x", padx=6, pady=3)

        label = ctk.CTkLabel(
            item,
            text=text,
            text_color=APP_COLORS["text"],
            anchor="w"
        )
        label.pack(fill="x", padx=10, pady=8)

    def _empty_state(self, text: str):
        ctk.CTkLabel(
            self.scroll,
            text=text,
            text_color=APP_COLORS["muted"]
        ).pack(pady=20)

    def get_commit_message(self) -> str:
        return self.commit_msg.get("1.0", "end").strip()

    def clear_commit_message(self):
        self.commit_msg.delete("1.0", "end")

    def set_commit_message(self, text: str):
        self.commit_msg.delete("1.0", "end")
        self.commit_msg.insert("1.0", text)