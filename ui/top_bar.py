import customtkinter as ctk

from ui.theme import APP_COLORS, load_icon


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_select_repo, on_action, on_branch_change=None):
        super().__init__(
            master,
            fg_color=APP_COLORS["topbar"],
            corner_radius=0,
            height=68
        )

        self.on_select_repo = on_select_repo
        self.on_action = on_action
        self.on_branch_change = on_branch_change

        self.repo_var = ctk.StringVar(value="Selecione um repositório")
        self.branch_var = ctk.StringVar(value="Nenhuma branch")

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=6)
        self.grid_columnconfigure(2, weight=2)

        self._build_left_section()
        self._build_center_section()
        self._build_right_section()

    def _build_left_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="w", padx=12, pady=6)

        ctk.CTkLabel(
            frame,
            text="repository",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=11)
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.repo_menu = ctk.CTkOptionMenu(
            frame,
            values=["Selecione um repositório"],
            variable=self.repo_var,
            width=190,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=12)
        )
        self.repo_menu.grid(row=1, column=0, padx=(0, 8), pady=(4, 0))

        self.open_repo_btn = self._create_secondary_button(
            frame,
            text="Abrir",
            icon_name="repo.png",
            command=self.on_select_repo,
            width=86
        )
        self.open_repo_btn.grid(row=1, column=1, padx=(0, 12), pady=(4, 0))

        ctk.CTkLabel(
            frame,
            text="branch",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=11)
        ).grid(row=0, column=2, sticky="w", padx=(0, 6))

        self.branch_menu = ctk.CTkOptionMenu(
            frame,
            values=["Nenhuma branch"],
            variable=self.branch_var,
            width=170,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            command=self._handle_branch_menu_change,
            state="disabled"
        )
        self.branch_menu.grid(row=1, column=2, padx=(0, 8), pady=(4, 0))

        self.refresh_btn = self._create_icon_button(
            frame,
            icon_name="refresh.png",
            command=lambda: self.on_action("Refresh")
        )
        self.refresh_btn.grid(row=1, column=3, padx=(0, 0), pady=(4, 0))

    def _build_center_section(self):
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=0, column=1, sticky="nsew", padx=10, pady=6)

        groups = [
            [("Undo", "undo.png"), ("Redo", "redo.png")],
            [("Pull", "pull.png"), ("Push", "push.png"), ("Branch", "branch.png"), ("Stash", "stash.png"),
             ("Pop", "pop.png")],
            [("Terminal", "terminal.png")],
        ]

        col = 0
        for group_index, group in enumerate(groups):
            group_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
            group_frame.grid(row=0, column=col, sticky="w")

            for index, (label, icon_name) in enumerate(group):
                button = self._create_toolbar_button(
                    group_frame,
                    text=label,
                    icon_name=icon_name,
                    command=lambda action=label: self.on_action(action),
                    width=88 if label in {"Undo", "Redo"} else 94
                )
                button.grid(row=0, column=index, padx=3, pady=0)

            col += 1

            if group_index < len(groups) - 1:
                sep = ctk.CTkFrame(
                    wrapper,
                    fg_color="#4b5363",
                    width=1,
                    height=28
                )
                sep.grid(row=0, column=col, padx=16, pady=0, sticky="ns")
                col += 1

    def _build_right_section(self):
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=0, column=2, sticky="e", padx=12, pady=6)

        actions = [
            ("Actions", "actions.png", 96),
            ("Search", "search.png", 88),
            ("Profile", "profile.png", 90),
        ]

        for index, (label, icon_name, width) in enumerate(actions):
            button = self._create_secondary_button(
                wrapper,
                text=label,
                icon_name=icon_name,
                command=lambda action=label: self.on_action(action),
                width=width
            )
            button.grid(row=0, column=index, padx=4, pady=0)

    def _create_toolbar_button(self, master, text, icon_name, command, width=92):
        btn = ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon_name, size=(22, 22)),
            compound="left",
            anchor="center",
            width=width,
            height=38,
            command=lambda: self._handle_click(btn, command),
            fg_color="transparent",
            hover_color=APP_COLORS["hover"],
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=6,
            font=ctk.CTkFont(size=12, weight="bold")
        )

        return btn

    def _create_secondary_button(self, master, text, icon_name, command, width=92):
        return ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon_name, size=(30, 30)),
            compound="left",
            anchor="center",
            width=width,
            height=32,
            command=command,
            fg_color="#3b414d",
            hover_color="#4b5563",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            font=ctk.CTkFont(size=11)
        )

    def _create_icon_button(self, master, icon_name, command):
        return ctk.CTkButton(
            master,
            text="",
            image=load_icon(icon_name, size=(22, 22)),
            width=32,
            height=32,
            command=command,
            fg_color="#3b414d",
            hover_color="#2563EB",
            corner_radius=8,
            border_width=0
        )

    def _handle_branch_menu_change(self, selected_branch: str):
        if selected_branch == "Nenhuma branch":
            return

        if self.on_branch_change:
            self.on_branch_change(selected_branch)

    def set_repositories(self, repo_names: list[str], current_name: str):
        values = repo_names if repo_names else ["Selecione um repositório"]
        self.repo_menu.configure(values=values)
        self.repo_var.set(current_name if current_name else values[0])

    def set_branches(self, branches: list[str], current_branch: str = ""):
        if not branches:
            self.branch_menu.configure(values=["Nenhuma branch"], state="disabled")
            self.branch_var.set("Nenhuma branch")
            return

        self.branch_menu.configure(values=branches, state="normal")
        self.branch_var.set(current_branch if current_branch in branches else branches[0])

    def set_selected_branch(self, branch_name: str):
        if not branch_name:
            self.branch_var.set("Nenhuma branch")
            return

        self.branch_var.set(branch_name)

    def get_selected_repository(self) -> str:
        return self.repo_var.get()

    def get_selected_branch(self) -> str:
        return self.branch_var.get()

    def _handle_click(self, button, command):
        # resetar todos
        for child in button.master.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(fg_color="transparent")

        # ativar atual
        button.configure(fg_color=APP_COLORS["primary"])

        command()
