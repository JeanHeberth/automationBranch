import customtkinter as ctk
from ui.theme import APP_COLORS


class FileSection(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, fg_color="transparent")

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title_label.pack(anchor="w", padx=4, pady=(3, 5))

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="x", expand=False)

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def set_files(self, files: list[str]):
        self.clear()

        if not files:
            empty = ctk.CTkLabel(
                self.container,
                text="Nenhum arquivo",
                text_color=APP_COLORS["muted"],
                anchor="w",
                font=ctk.CTkFont(size=11)
            )
            empty.pack(fill="x", padx=6, pady=(0, 6))
            return

        for file_text in files:
            item = ctk.CTkFrame(
                self.container,
                fg_color="#2a2f3a",
                corner_radius=8,
                height=32
            )
            item.pack(fill="x", padx=4, pady=2)

            label = ctk.CTkLabel(
                item,
                text=file_text,
                text_color=APP_COLORS["text"],
                anchor="w",
                font=ctk.CTkFont(size=11)
            )
            label.pack(fill="x", padx=8, pady=6)


class RightPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0
        )

        self.commit_placeholder = "Digite a mensagem do commit..."
        self.is_placeholder_active = True

        self._build_header()
        self._build_file_list()
        self._build_commit_area()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=42)
        header.pack(fill="x", padx=8, pady=(6, 3))

        self.title = ctk.CTkLabel(
            header,
            text="Changes / Commit",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.title.pack(side="left")

    def _build_file_list(self):
        self.files_container = ctk.CTkFrame(self, fg_color="transparent")
        self.files_container.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(
            self.files_container,
            fg_color="transparent",
            height=240
        )
        self.scroll.pack(fill="both", expand=True)

        self.staged_section = FileSection(self.scroll, "Staged Files")
        self.staged_section.pack(fill="x", pady=(0, 8))

        self.unstaged_section = FileSection(self.scroll, "Unstaged Files")
        self.unstaged_section.pack(fill="x", pady=(0, 8))

    def _build_commit_area(self):
        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=8, pady=(3, 6))

        commit_container = ctk.CTkFrame(self, fg_color="transparent")
        commit_container.pack(fill="x", padx=8, pady=(0, 8))

        commit_title = ctk.CTkLabel(
            commit_container,
            text="Mensagem de commit",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        commit_title.pack(anchor="w", pady=(0, 5))

        self.commit_msg = ctk.CTkTextbox(
            commit_container,
            height=92,
            corner_radius=8,
            fg_color="#2a2f3a",
            text_color=APP_COLORS["muted"],
            border_width=1,
            border_color=APP_COLORS["border"]
        )
        self.commit_msg.pack(fill="x", pady=(0, 8))
        self.commit_msg.insert("1.0", self.commit_placeholder)

        self.commit_msg.bind("<FocusIn>", self._handle_commit_focus_in)
        self.commit_msg.bind("<FocusOut>", self._handle_commit_focus_out)

        self.commit_btn = ctk.CTkButton(
            commit_container,
            text="Commit",
            height=36,
            fg_color=APP_COLORS["accent"],
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.commit_btn.pack(fill="x")

    def _handle_commit_focus_in(self, _event=None):
        if self.is_placeholder_active:
            self.commit_msg.delete("1.0", "end")
            self.commit_msg.configure(text_color=APP_COLORS["text"])
            self.is_placeholder_active = False

    def _handle_commit_focus_out(self, _event=None):
        content = self.commit_msg.get("1.0", "end").strip()

        if not content:
            self._restore_placeholder()

    def _restore_placeholder(self):
        self.commit_msg.delete("1.0", "end")
        self.commit_msg.insert("1.0", self.commit_placeholder)
        self.commit_msg.configure(text_color=APP_COLORS["muted"])
        self.is_placeholder_active = True

    def set_files_grouped(self, staged_files: list[str], unstaged_files: list[str]):
        self.staged_section.set_files(staged_files)
        self.unstaged_section.set_files(unstaged_files)

    def set_files(self, files: list[str]):
        self.staged_section.set_files(files)
        self.unstaged_section.set_files([])

    def get_commit_message(self) -> str:
        if self.is_placeholder_active:
            return ""
        return self.commit_msg.get("1.0", "end").strip()

    def clear_commit_message(self):
        self._restore_placeholder()

    def set_commit_message(self, text: str):
        self.commit_msg.delete("1.0", "end")
        self.commit_msg.insert("1.0", text)
        self.commit_msg.configure(text_color=APP_COLORS["text"])
        self.is_placeholder_active = False

    def set_on_commit(self, callback):
        self.commit_btn.configure(command=callback)