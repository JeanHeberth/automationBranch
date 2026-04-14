import customtkinter as ctk
from ui.theme import APP_COLORS


class RightPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0,
            width=320
        )

        ctk.CTkLabel(
            self,
            text="Changes / Commit",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.files_box = ctk.CTkTextbox(self, height=180, corner_radius=8)
        self.files_box.pack(fill="x", padx=16, pady=(0, 12))
        self.set_files(["src/test/java/.../DepartamentoServiceTest.java"])

        self.commit_msg = ctk.CTkTextbox(self, height=120, corner_radius=8)
        self.commit_msg.pack(fill="x", padx=16, pady=(0, 12))
        self.commit_msg.insert("1.0", "Commit summary")

        self.commit_btn = ctk.CTkButton(self, text="Commit")
        self.commit_btn.pack(fill="x", padx=16, pady=(0, 16))

    def set_files(self, files: list[str]):
        self.files_box.configure(state="normal")
        self.files_box.delete("1.0", "end")
        self.files_box.insert("1.0", "\n".join(files))
        self.files_box.configure(state="disabled")