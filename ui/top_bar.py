import customtkinter as ctk
from ui.theme import APP_COLORS, load_icon


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_select_repo, on_action, on_branch_change=None):
        super().__init__(
            master,
            fg_color=APP_COLORS["topbar"],
            corner_radius=0,
            height=60
        )

        self.on_select_repo = on_select_repo
        self.on_action = on_action
        self.on_branch_change = on_branch_change

        self.repo_var = ctk.StringVar(value="Selecione um repositório")
        self.branch_var = ctk.StringVar(value="Nenhuma branch")

        self.hidden_actions = []
        self._responsive_job = None
        self._size_mode = "large"

        self.grid_columnconfigure(0, weight=0, minsize=250)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=108)

        self._build_left_section()
        self._build_center_section()
        self._build_right_section()

        self.bind("<Configure>", self._schedule_responsive_update)
        self.after(120, self._apply_responsive_layout)

    # =========================
    # LEFT
    # =========================
    def _build_left_section(self):
        self.left_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.left_wrapper.grid(row=0, column=0, sticky="w", padx=8, pady=5)

        repo_block = ctk.CTkFrame(self.left_wrapper, fg_color="transparent")
        repo_block.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            repo_block,
            text="repository",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=9)
        ).pack(anchor="w", pady=(0, 2))

        repo_row = ctk.CTkFrame(repo_block, fg_color="transparent")
        repo_row.pack(anchor="w")

        self.repo_menu = ctk.CTkOptionMenu(
            repo_row,
            values=["Selecione um repositório"],
            variable=self.repo_var,
            width=126,
            height=31,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=10)
        )
        self.repo_menu.pack(side="left", padx=(0, 5))

        self.open_repo_btn = self._create_secondary_button(
            repo_row,
            text="Abrir",
            icon="repo.png",
            command=self.on_select_repo,
            width=64
        )
        self.open_repo_btn.pack(side="left")

        branch_block = ctk.CTkFrame(self.left_wrapper, fg_color="transparent")
        branch_block.pack(side="left")

        ctk.CTkLabel(
            branch_block,
            text="branch",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=9)
        ).pack(anchor="w", pady=(0, 2))

        branch_row = ctk.CTkFrame(branch_block, fg_color="transparent")
        branch_row.pack(anchor="w")

        self.branch_menu = ctk.CTkOptionMenu(
            branch_row,
            values=["Nenhuma branch"],
            variable=self.branch_var,
            width=108,
            height=31,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=10),
            command=self._handle_branch_menu_change,
            state="disabled"
        )
        self.branch_menu.pack(side="left", padx=(0, 5))

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
        self.center_wrapper.grid(row=0, column=1, sticky="nsew", padx=3, pady=5)

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
                sep.grid(row=0, column=col, padx=5, pady=7, sticky="ns")
                col += 1

    def _get_visible_center_actions(self):
        width = max(self.center_wrapper.winfo_width(), 1)

        actions = [
            "Undo", "Redo",
            "Pull", "Push", "Branch",
            "Delete Branch", "Stash", "Pop",
            "Open PR", "Merge PR", "Terminal"
        ]

        if width >= 700:
            self.hidden_actions = []
            return actions

        if width >= 635:
            self.hidden_actions = ["Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 575:
            self.hidden_actions = ["Stash", "Pop", "Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 520:
            self.hidden_actions = ["Delete Branch", "Stash", "Pop", "Terminal"]
            return [a for a in actions if a not in self.hidden_actions]

        if width >= 470:
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
            text="",
            icon="actions.png",
            command=lambda: self.on_action("Actions"),
            width=32
        )
        self.actions_btn.pack(side="left", padx=(0, 4))

        self.search_btn = self._create_secondary_button(
            self.right_wrapper,
            text="",
            icon="search.png",
            command=lambda: self.on_action("Search"),
            width=32
        )
        self.search_btn.pack(side="left", padx=(0, 4))

        self.profile_btn = self._create_secondary_button(
            self.right_wrapper,
            text="",
            icon="profile.png",
            command=lambda: self.on_action("Profile"),
            width=32
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

        if total_width >= 1240:
            self._size_mode = "large"
        elif total_width >= 980:
            self._size_mode = "medium"
        else:
            self._size_mode = "small"

        if center_width < 500:
            self._size_mode = "small"
        elif center_width < 600 and self._size_mode == "large":
            self._size_mode = "medium"

        self._apply_left()
        self._apply_right()
        self._render_center_toolbar()

    def _apply_left(self):
        if self._size_mode == "large":
            self.repo_menu.configure(width=126)
            self.branch_menu.configure(width=108)
            self.open_repo_btn.configure(text="Abrir", width=64)
            self.grid_columnconfigure(0, minsize=250)
            return

        if self._size_mode == "medium":
            self.repo_menu.configure(width=98)
            self.branch_menu.configure(width=86)
            self.open_repo_btn.configure(text="", width=30)
            self.grid_columnconfigure(0, minsize=202)
            return

        self.repo_menu.configure(width=88)
        self.branch_menu.configure(width=78)
        self.open_repo_btn.configure(text="", width=30)
        self.grid_columnconfigure(0, minsize=188)

    def _apply_right(self):
        self.actions_btn.configure(text="", width=32)
        self.search_btn.configure(text="", width=32)
        self.profile_btn.configure(text="", width=32)
        self.grid_columnconfigure(2, minsize=108)

    # =========================
    # BUTTONS
    # =========================
    def _create_toolbar_button(self, master, text, icon, command):
        show_text = self._size_mode != "small"

        icon_only_in_medium = {"Delete Branch", "Stash", "Pop", "Terminal"}

        if self._size_mode == "medium" and text in icon_only_in_medium:
            button_text = ""
        else:
            text_map = {
                "Open PR": "PR" if self._size_mode == "medium" else "Open PR",
                "Merge PR": "Merge" if self._size_mode == "medium" else "Merge PR",
                "Delete Branch": "Delete" if self._size_mode == "medium" else "Delete Branch",
            }
            button_text = text_map.get(text, text)

        width_map = {
            "Undo": 50,
            "Redo": 50,
            "Pull": 50,
            "Push": 50,
            "Branch": 54,
            "Delete Branch": 30,
            "Delete": 56,
            "Stash": 30,
            "Pop": 30,
            "Open PR": 60,
            "PR": 42,
            "Merge PR": 68,
            "Merge": 50,
            "Terminal": 30,
        }

        if not show_text:
            width = 30
            button_text = ""
        else:
            width = width_map.get(button_text or text, 50)

        return ctk.CTkButton(
            master,
            text=button_text,
            image=load_icon(icon, size=(14, 14), padding=1),
            compound="left",
            anchor="center",
            height=30,
            width=width,
            fg_color="transparent",
            hover_color="#2e3948",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=4 if button_text else 0,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=command
        )

    def _create_secondary_button(self, master, text, icon, command, width=70):
        show_text = bool(text)

        return ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon, size=(14, 14), padding=1),
            compound="left",
            anchor="center",
            width=width,
            height=30,
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
            image=load_icon(icon, size=(14, 14), padding=1),
            width=30,
            height=30,
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
        self.profile_btn.configure(text="", width=32)

    def get_selected_repository(self) -> str:
        return self.repo_var.get()

    def get_selected_branch(self) -> str:
        return self.branch_var.get()