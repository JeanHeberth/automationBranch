import customtkinter as ctk

from ui.theme import APP_COLORS, load_icon


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_select_repo, on_action):
        super().__init__(
            master,
            fg_color=APP_COLORS["topbar"],
            corner_radius=0,
            height=86
        )

        self.on_select_repo = on_select_repo
        self.on_action = on_action

        self.repo_var = ctk.StringVar(value="Selecione um repositório")
        self.branch_var = ctk.StringVar(value="main")

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=5)
        self.grid_columnconfigure(2, weight=2)

        self._build_left_section()
        self._build_center_section()
        self._build_right_section()

    def _build_left_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="w", padx=12, pady=8)

        ctk.CTkLabel(
            frame,
            text="repository",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.repo_menu = ctk.CTkOptionMenu(
            frame,
            values=["Selecione um repositório"],
            variable=self.repo_var,
            width=190,
            height=34,
            fg_color=APP_COLORS["panel"],
            button_color="#4b5563",
            button_hover_color="#5b6472",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=13)
        )
        self.repo_menu.grid(row=1, column=0, padx=(0, 8), pady=(4, 0))

        self.open_repo_btn = self._create_toolbar_button(
            frame,
            text="Abrir",
            icon_name="repo.png",
            command=self.on_select_repo,
            width=88
        )
        self.open_repo_btn.grid(row=1, column=1, padx=(0, 12), pady=(4, 0))

        ctk.CTkLabel(
            frame,
            text="branch",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12)
        ).grid(row=0, column=2, sticky="w", padx=(0, 6))

        self.branch_menu = ctk.CTkOptionMenu(
            frame,
            values=["main", "develop"],
            variable=self.branch_var,
            width=170,
            height=34,
            fg_color=APP_COLORS["panel"],
            button_color="#4b5563",
            button_hover_color="#5b6472",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=13)
        )
        self.branch_menu.grid(row=1, column=2, padx=(0, 8), pady=(4, 0))

        self.refresh_btn = self._create_icon_button(
            frame,
            icon_name="refresh.png",
            command=lambda: self.on_action("Refresh")
        )
        self.refresh_btn.grid(row=1, column=3, padx=(0, 0), pady=(4, 0))

    def _build_center_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        actions = [
            ("Undo", "undo.png"),
            ("Redo", "redo.png"),
            ("Pull", "pull.png"),
            ("Push", "push.png"),
            ("Branch", "branch.png"),
            ("Stash", "stash.png"),
            ("Pop", "pop.png"),
            ("Terminal", "terminal.png"),
        ]

        for index, (label, icon_name) in enumerate(actions):
            button = self._create_toolbar_button(
                frame,
                text=label,
                icon_name=icon_name,
                command=lambda action=label: self.on_action(action),
                width=92
            )
            button.grid(row=0, column=index, padx=4, pady=2)

    def _build_right_section(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=2, sticky="e", padx=12, pady=8)

        actions = [
            ("Actions", "actions.png", 98),
            ("Search", "search.png", 92),
            ("Profile", "profile.png", 92),
        ]

        for index, (label, icon_name, width) in enumerate(actions):
            button = self._create_toolbar_button(
                frame,
                text=label,
                icon_name=icon_name,
                command=lambda action=label: self.on_action(action),
                width=width
            )
            button.grid(row=0, column=index, padx=4, pady=2)

    def _create_toolbar_button(self, master, text, icon_name, command, width=96):
        return ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon_name, size=(18, 18)),
            compound="left",
            anchor="center",
            width=width,
            height=34,
            command=command,
            fg_color="#3b414d",
            hover_color="#4a5160",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            font=ctk.CTkFont(size=12)
        )

    def _create_icon_button(self, master, icon_name, command):
        return ctk.CTkButton(
            master,
            text="",
            image=load_icon(icon_name, size=(18, 18)),
            width=34,
            height=34,
            command=command,
            fg_color="#3b414d",
            hover_color="#4a5160",
            corner_radius=8,
            border_width=0
        )

    def set_repositories(self, repo_names: list[str], current_name: str):
        values = repo_names if repo_names else ["Selecione um repositório"]
        self.repo_menu.configure(values=values)
        self.repo_var.set(current_name if current_name else values[0])

    def set_branches(self, branches: list[str], current_branch: str = "main"):
        values = branches if branches else ["main"]
        self.branch_menu.configure(values=values)
        self.branch_var.set(current_branch if current_branch in values else values[0])

    def get_selected_repository(self) -> str:
        return self.repo_var.get()

    def get_selected_branch(self) -> str:
        return self.branch_var.get()