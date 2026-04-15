import customtkinter as ctk
from ui.theme import APP_COLORS, load_icon


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_select_repo, on_action, on_branch_change=None):
        super().__init__(
            master,
            fg_color=APP_COLORS["topbar"],
            corner_radius=0,
            height=62
        )

        self.on_select_repo = on_select_repo
        self.on_action = on_action
        self.on_branch_change = on_branch_change

        self.repo_var = ctk.StringVar(value="Selecione um repositório")
        self.branch_var = ctk.StringVar(value="Nenhuma branch")

        self.hidden_actions = []
        self._responsive_job = None
        self._size_mode = "large"

        self.grid_columnconfigure(0, weight=0, minsize=282)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=116)

        self._build_left_section()
        self._build_center_section()
        self._build_right_section()

        self.bind("<Configure>", self._schedule_responsive_update)
        self.after(100, self._apply_responsive_layout)

    # =========================
    # LEFT
    # =========================
    def _build_left_section(self):
        self.left_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.left_wrapper.grid(row=0, column=0, sticky="w", padx=8, pady=5)

        repo_block = ctk.CTkFrame(self.left_wrapper, fg_color="transparent")
        repo_block.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            repo_block,
            text="repository",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10)
        ).pack(anchor="w", pady=(0, 2))

        repo_row = ctk.CTkFrame(repo_block, fg_color="transparent")
        repo_row.pack(anchor="w")

        self.repo_menu = ctk.CTkOptionMenu(
            repo_row,
            values=["Selecione um repositório"],
            variable=self.repo_var,
            width=134,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=11)
        )
        self.repo_menu.pack(side="left", padx=(0, 6))

        self.open_repo_btn = self._create_secondary_button(
            repo_row,
            text="Abrir",
            icon="repo.png",
            command=self.on_select_repo,
            width=68
        )
        self.open_repo_btn.pack(side="left")

        branch_block = ctk.CTkFrame(self.left_wrapper, fg_color="transparent")
        branch_block.pack(side="left")

        ctk.CTkLabel(
            branch_block,
            text="branch",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10)
        ).pack(anchor="w", pady=(0, 2))

        branch_row = ctk.CTkFrame(branch_block, fg_color="transparent")
        branch_row.pack(anchor="w")

        self.branch_menu = ctk.CTkOptionMenu(
            branch_row,
            values=["Nenhuma branch"],
            variable=self.branch_var,
            width=114,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            command=self._handle_branch_menu_change,
            state="disabled"
        )
        self.branch_menu.pack(side="left", padx=(0, 6))

        self.refresh_btn = self._create_primary_icon_button(
            branch_row,
            icon="refresh.png",
            command=lambda: self.on_action("Refresh")
        )
        self.refresh_btn.pack(side="left")

    # =========================
    # CENTER
    # =========================
    def _build_center_section(self):
        self.center_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.center_wrapper.grid(row=0, column=1, sticky="nsew", padx=4, pady=5)

        self.toolbar_groups = [
            [("Undo", "undo.png"), ("Redo", "redo.png")],
            [
                ("Pull", "pull.png"),
                ("Push", "push.png"),
                ("Branch", "branch.png"),
                ("Delete Branch", "delete_branch.png"),
                ("Stash", "stash.png"),
                ("Pop", "pop.png"),
            ],
            [
                ("Open PR", "open_pr.png"),
                ("Merge PR", "merge_pr.png"),
                ("Terminal", "terminal.png"),
            ],
        ]

        self._render_center_toolbar()

    def _render_center_toolbar(self):
        for child in self.center_wrapper.winfo_children():
            child.destroy()

        visible_actions = self._get_visible_center_actions()

        col = 0
        visible_group_indexes = []
        for idx, group in enumerate(self.toolbar_groups):
            if any(label in visible_actions for label, _ in group):
                visible_group_indexes.append(idx)

        for group_index in visible_group_indexes:
            group = self.toolbar_groups[group_index]
            visible_group = [(label, icon) for label, icon in group if label in visible_actions]

            group_frame = ctk.CTkFrame(self.center_wrapper, fg_color="transparent")
            group_frame.grid(row=0, column=col, sticky="w")

            for idx, (label, icon) in enumerate(visible_group):
                btn = self._create_toolbar_button(
                    group_frame,
                    text=label,
                    icon=icon,
                    command=lambda a=label: self.on_action(a)
                )
                btn.grid(row=0, column=idx, padx=1)

            col += 1

            if group_index != visible_group_indexes[-1]:
                sep = ctk.CTkFrame(
                    self.center_wrapper,
                    fg_color="#445064",
                    width=1,
                    height=18
                )
                sep.grid(row=0, column=col, padx=6, pady=7, sticky="ns")
                col += 1

    def _get_visible_center_actions(self):
        width = max(self.center_wrapper.winfo_width(), 1)

        actions = [
            "Undo", "Redo",
            "Pull", "Push", "Branch",
            "Delete Branch", "Stash", "Pop",
            "Open PR", "Merge PR", "Terminal"
        ]

        if width >= 720:
            self.hidden_actions = []
            return actions

        if width >= 650:
            self.hidden_actions = ["Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 590:
            self.hidden_actions = ["Stash", "Pop", "Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 540:
            self.hidden_actions = ["Delete Branch", "Stash", "Pop", "Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 485:
            self.hidden_actions = ["Branch", "Delete Branch", "Stash", "Pop", "Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        self.hidden_actions = ["Branch", "Delete Branch", "Stash", "Pop", "Open PR", "Merge PR", "Terminal"]
        return ["Undo", "Redo", "Pull", "Push"]

    # =========================
    # RIGHT
    # =========================
    def _build_right_section(self):
        self.right_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.right_wrapper.grid(row=0, column=2, sticky="e", padx=8, pady=5)

        self.actions_btn = self._create_secondary_button(
            self.right_wrapper,
            text="Actions",
            icon="actions.png",
            command=lambda: self.on_action("Actions"),
            width=78
        )
        self.actions_btn.pack(side="left", padx=(0, 4))

        self.search_btn = self._create_secondary_button(
            self.right_wrapper,
            text="Search",
            icon="search.png",
            command=lambda: self.on_action("Search"),
            width=68
        )
        self.search_btn.pack(side="left", padx=(0, 4))

        self.profile_btn = self._create_secondary_button(
            self.right_wrapper,
            text="GitHub",
            icon="profile.png",
            command=lambda: self.on_action("Profile"),
            width=74
        )
        self.profile_btn.pack(side="left")

    # =========================
    # RESPONSIVE
    # =========================
    def _schedule_responsive_update(self, _event=None):
        if self._responsive_job:
            self.after_cancel(self._responsive_job)
        self._responsive_job = self.after(60, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        self._responsive_job = None

        total_width = max(self.winfo_width(), 1)
        center_width = max(self.center_wrapper.winfo_width(), 1)

        if total_width >= 1220:
            self._size_mode = "large"
        elif total_width >= 980:
            self._size_mode = "medium"
        else:
            self._size_mode = "small"

        if center_width < 500:
            self._size_mode = "small"
        elif center_width < 610 and self._size_mode == "large":
            self._size_mode = "medium"

        self._apply_left()
        self._apply_right()
        self._render_center_toolbar()

    def _apply_left(self):
        if self._size_mode == "large":
            self.repo_menu.configure(width=134)
            self.branch_menu.configure(width=114)
            self.open_repo_btn.configure(text="Abrir", width=68)
            self.grid_columnconfigure(0, minsize=282)
            return

        if self._size_mode == "medium":
            self.repo_menu.configure(width=104)
            self.branch_menu.configure(width=92)
            self.open_repo_btn.configure(text="", width=32)
            self.grid_columnconfigure(0, minsize=224)
            return

        self.repo_menu.configure(width=90)
        self.branch_menu.configure(width=80)
        self.open_repo_btn.configure(text="", width=30)
        self.grid_columnconfigure(0, minsize=206)

    def _apply_right(self):
        # No notebook, direita sempre compacta
        if self._size_mode == "large":
            self.actions_btn.configure(text="Actions", width=78)
            self.search_btn.configure(text="Search", width=68)
            self.profile_btn.configure(text="GitHub", width=74)
            self.grid_columnconfigure(2, minsize=116)
            return

        self.actions_btn.configure(text="", width=32)
        self.search_btn.configure(text="", width=32)
        self.profile_btn.configure(text="", width=32)
        self.grid_columnconfigure(2, minsize=116)

    # =========================
    # BUTTONS
    # =========================
    def _create_toolbar_button(self, master, text, icon, command):
        show_text = self._size_mode != "small"

        text_map = {
            "Merge PR": "Merge" if self._size_mode == "medium" else "Merge PR",
            "Delete Branch": "Delete" if self._size_mode == "medium" else "Delete Branch",
        }

        button_text = text_map.get(text, text)

        width_map = {
            "Undo": 54,
            "Redo": 54,
            "Pull": 54,
            "Push": 54,
            "Branch": 60,
            "Delete Branch": 82,
            "Delete": 62,
            "Stash": 54,
            "Pop": 50,
            "Open PR": 66,
            "Merge PR": 72,
            "Merge": 56,
            "Terminal": 64,
        }

        if not show_text:
            width = 32
        else:
            width = width_map.get(button_text, 54)

        return ctk.CTkButton(
            master,
            text=button_text if show_text else "",
            image=load_icon(icon, size=(15, 15), padding=1),
            compound="left",
            anchor="center",
            height=31,
            width=width,
            fg_color="transparent",
            hover_color="#2e3948",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=4 if show_text else 0,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=command
        )

    def _create_secondary_button(self, master, text, icon, command, width=70):
        show_text = bool(text)

        return ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon, size=(15, 15), padding=1),
            compound="left",
            anchor="center",
            width=width,
            height=31,
            fg_color="#394454",
            hover_color="#465365",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=4 if show_text else 0,
            font=ctk.CTkFont(size=10),
            command=command
        )

    def _create_primary_icon_button(self, master, icon, command):
        return ctk.CTkButton(
            master,
            text="",
            image=load_icon(icon, size=(15, 15), padding=1),
            width=32,
            height=31,
            fg_color="#1d8fe1",
            hover_color="#2ea4f7",
            corner_radius=8,
            border_width=0,
            command=command
        )

    # =========================
    # PUBLIC API
    # =========================
    def _handle_branch_menu_change(self, branch):
        if branch == "Nenhuma branch":
            return
        if self.on_branch_change:
            self.on_branch_change(branch)

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

    def set_profile_label(self, text: str):
        if self._size_mode == "large":
            self.profile_btn.configure(text=text, width=74)
        else:
            self.profile_btn.configure(text="", width=32)

    def get_selected_repository(self) -> str:
        return self.repo_var.get()

    def get_selected_branch(self) -> str:
        return self.branch_var.get()