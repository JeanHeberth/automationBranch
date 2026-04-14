import customtkinter as ctk
from ui.theme import APP_COLORS


class LeftSidebar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["sidebar"],
            corner_radius=0,
            width=260
        )

        ctk.CTkLabel(
            self,
            text="Branches",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.search = ctk.CTkEntry(self, placeholder_text="Filtrar branches...")
        self.search.pack(fill="x", padx=16, pady=(0, 12))

        self.branch_list = ctk.CTkTextbox(self, corner_radius=8)
        self.branch_list.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.set_branches(["main", "develop", "feature/ui-topbar"])

    def set_branches(self, branches: list[str]):
        self.branch_list.configure(state="normal")
        self.branch_list.delete("1.0", "end")
        self.branch_list.insert("1.0", "\n".join(branches))
        self.branch_list.configure(state="disabled")