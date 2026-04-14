import customtkinter as ctk
from ui.theme import APP_COLORS


class CenterPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["bg"],
            corner_radius=0
        )

        ctk.CTkLabel(
            self,
            text="Commits",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.commits = ctk.CTkTextbox(self, corner_radius=8)
        self.commits.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.set_commits([
            "// WIP",
            "Merge pull request #41 alterando-arquivo",
            "Criado arquivo .yml",
            "Merge pull request #40 criando-sse",
            "criado um server.address",
            "Merge pull request #39 CAE-36",
        ])

    def set_commits(self, commits: list[str]):
        self.commits.configure(state="normal")
        self.commits.delete("1.0", "end")
        self.commits.insert("1.0", "\n".join(commits))
        self.commits.configure(state="disabled")