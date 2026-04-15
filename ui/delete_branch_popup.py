import customtkinter as ctk
from ui.theme import APP_COLORS


class DeleteBranchPopup(ctk.CTkToplevel):
    def __init__(self, master, local_branches: list[str], remote_branches: list[str], on_confirm):
        super().__init__(master)

        self.local_branches = local_branches
        self.remote_branches = remote_branches
        self.on_confirm = on_confirm

        self.mode_var = ctk.StringVar(value="specific")
        self.location_var = ctk.StringVar(value="local")
        self.search_var = ctk.StringVar(value="")
        self.branch_var = ctk.StringVar(value="")

        self.filtered_branches: list[str] = []

        self.title("Deletar Branch")
        self.geometry("520x800")
        self.resizable(False, False)
        self.configure(fg_color=APP_COLORS["panel"])

        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._center(master)
        self._refresh_branch_options()

    def _build_ui(self):
        container = ctk.CTkFrame(
            self,
            fg_color=APP_COLORS["panel"],
            corner_radius=12
        )
        container.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            container,
            text="Deletar Branch",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", pady=(4, 10))

        ctk.CTkLabel(
            container,
            text="Escolha se deseja deletar uma branch específica ou todas, exceto as protegidas.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12),
            justify="left",
            wraplength=440
        ).pack(anchor="w", pady=(0, 14))

        mode_frame = ctk.CTkFrame(container, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            mode_frame,
            text="Tipo de deleção",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w")

        ctk.CTkRadioButton(
            mode_frame,
            text="Branch específica",
            variable=self.mode_var,
            value="specific",
            command=self._refresh_mode_state
        ).pack(anchor="w", pady=(6, 2))

        ctk.CTkRadioButton(
            mode_frame,
            text="Todas, exceto protegidas",
            variable=self.mode_var,
            value="all",
            command=self._refresh_mode_state
        ).pack(anchor="w")

        location_frame = ctk.CTkFrame(container, fg_color="transparent")
        location_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            location_frame,
            text="Onde deletar",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w")

        ctk.CTkRadioButton(
            location_frame,
            text="Local",
            variable=self.location_var,
            value="local",
            command=self._refresh_branch_options
        ).pack(anchor="w", pady=(6, 2))

        ctk.CTkRadioButton(
            location_frame,
            text="Remota",
            variable=self.location_var,
            value="remote",
            command=self._refresh_branch_options
        ).pack(anchor="w")

        branch_frame = ctk.CTkFrame(container, fg_color="transparent")
        branch_frame.pack(fill="both", expand=True, pady=(0, 12))

        ctk.CTkLabel(
            branch_frame,
            text="Buscar branch",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", pady=(0, 6))

        self.search_entry = ctk.CTkEntry(
            branch_frame,
            textvariable=self.search_var,
            placeholder_text="Digite para filtrar branches",
            height=36,
            corner_radius=8,
            fg_color="#1b1f27",
            border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(fill="x", pady=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_search_change)

        self.selected_label = ctk.CTkLabel(
            branch_frame,
            text="Nenhuma branch selecionada",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.selected_label.pack(fill="x", pady=(0, 6))

        self.branch_list = ctk.CTkScrollableFrame(
            branch_frame,
            fg_color="#111827",
            corner_radius=10,
            height=150
        )
        self.branch_list.pack(fill="both", expand=True)

        helper_frame = ctk.CTkFrame(container, fg_color="#1b2430", corner_radius=10)
        helper_frame.pack(fill="x", pady=(8, 14))

        ctk.CTkLabel(
            helper_frame,
            text="Protegidas automaticamente: main, master, develop, developer.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=11),
            justify="left",
            wraplength=420
        ).pack(anchor="w", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            helper_frame,
            text="A branch atual local também não pode ser deletada.",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=10, pady=(0, 8))

        actions = ctk.CTkFrame(container, fg_color="transparent")
        actions.pack(fill="x", pady=(0, 0))

        cancel_btn = ctk.CTkButton(
            actions,
            text="Cancelar",
            height=38,
            fg_color="transparent",
            hover_color="#1F2937",
            text_color=APP_COLORS["text"],
            border_width=1,
            border_color=APP_COLORS["border"],
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        confirm_btn = ctk.CTkButton(
            actions,
            text="Deletar",
            height=38,
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="#FFFFFF",
            corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._confirm
        )
        confirm_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))

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

    def _get_current_branch_source(self) -> list[str]:
        if self.location_var.get() == "local":
            return self.local_branches
        return self.remote_branches

    def _clear_branch_list(self):
        for widget in self.branch_list.winfo_children():
            widget.destroy()

    def _render_branch_list(self):
        self._clear_branch_list()

        if self.mode_var.get() == "all":
            ctk.CTkLabel(
                self.branch_list,
                text="Modo em massa selecionado.\nTodas as branches não protegidas serão deletadas.",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=12),
                justify="center"
            ).pack(expand=True, pady=20)
            return

        if not self.filtered_branches:
            ctk.CTkLabel(
                self.branch_list,
                text="Nenhuma branch encontrada.",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=12)
            ).pack(anchor="center", pady=20)
            return

        for branch in self.filtered_branches:
            fg_color = "#2563EB" if self.branch_var.get() == branch else "transparent"
            text_color = "#FFFFFF" if self.branch_var.get() == branch else APP_COLORS["text"]

            btn = ctk.CTkButton(
                self.branch_list,
                text=branch,
                height=34,
                fg_color=fg_color,
                hover_color="#374151" if fg_color == "transparent" else "#3B82F6",
                text_color=text_color,
                anchor="w",
                corner_radius=8,
                command=lambda b=branch: self._select_branch(b)
            )
            btn.pack(fill="x", padx=4, pady=3)

    def _select_branch(self, branch_name: str):
        self.branch_var.set(branch_name)
        self.selected_label.configure(text=f"Selecionada: {branch_name}", text_color=APP_COLORS["text"])
        self._render_branch_list()

    def _refresh_mode_state(self):
        is_all = self.mode_var.get() == "all"

        if is_all:
            self.search_entry.configure(state="disabled")
            self.selected_label.configure(
                text="Modo em massa ativo",
                text_color=APP_COLORS["muted"]
            )
        else:
            self.search_entry.configure(state="normal")
            if self.branch_var.get():
                self.selected_label.configure(
                    text=f"Selecionada: {self.branch_var.get()}",
                    text_color=APP_COLORS["text"]
                )
            else:
                self.selected_label.configure(
                    text="Nenhuma branch selecionada",
                    text_color=APP_COLORS["muted"]
                )

        self._refresh_branch_options()

    def _refresh_branch_options(self):
        branches = self._get_current_branch_source()
        term = self.search_var.get().strip().lower()

        if term:
            self.filtered_branches = [b for b in branches if term in b.lower()]
        else:
            self.filtered_branches = branches[:]

        if self.filtered_branches:
            current_selected = self.branch_var.get()
            if current_selected not in self.filtered_branches:
                self.branch_var.set(self.filtered_branches[0])

            if self.mode_var.get() == "specific":
                self.selected_label.configure(
                    text=f"Selecionada: {self.branch_var.get()}",
                    text_color=APP_COLORS["text"]
                )
        else:
            self.branch_var.set("")
            if self.mode_var.get() == "specific":
                self.selected_label.configure(
                    text="Nenhuma branch selecionada",
                    text_color=APP_COLORS["muted"]
                )

        self._render_branch_list()

    def _on_search_change(self, _event=None):
        self._refresh_branch_options()

    def _confirm(self):
        self.on_confirm(
            mode=self.mode_var.get(),
            location=self.location_var.get(),
            branch_name=self.branch_var.get()
        )
        self.destroy()