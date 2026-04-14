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
        self._build_list()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=48)
        header.pack(fill="x", padx=10, pady=(8, 4))

        self.title = ctk.CTkLabel(
            header,
            text="Arquivos",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title.pack(side="left")

    def _build_list(self):
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.scroll.pack(fill="both", expand=True, padx=6, pady=6)

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