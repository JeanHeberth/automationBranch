import customtkinter as ctk

from ui.theme import APP_COLORS, load_icon


class TopBar(ctk.CTkFrame):
    def __init__(self, master, on_select_repo, on_action, on_branch_change=None):
        super().__init__(
            master,
            fg_color=APP_COLORS["topbar"],
            corner_radius=0,
            height=64
        )

        self.on_select_repo = on_select_repo
        self.on_action = on_action
        self.on_branch_change = on_branch_change

        self.repo_var = ctk.StringVar(value="Selecione um repositório")
        self.branch_var = ctk.StringVar(value="Nenhuma branch")

        self.hidden_actions: list[str] = []
        self.actions_popup = None
        self._responsive_job = None
        self._size_mode = "large"

        self.grid_columnconfigure(0, weight=0, minsize=360)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=220)

        self._build_left_section()
        self._build_center_section()
        self._build_right_section()

        self.bind("<Configure>", self._schedule_responsive_update)
        self.after(80, self._apply_responsive_layout)

    # =========================
    # LEFT
    # =========================
    def _build_left_section(self):
        self.left_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.left_wrapper.grid(row=0, column=0, sticky="w", padx=10, pady=6)

        ctk.CTkLabel(
            self.left_wrapper,
            text="repository",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10)
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        self.repo_menu = ctk.CTkOptionMenu(
            self.left_wrapper,
            values=["Selecione um repositório"],
            variable=self.repo_var,
            width=160,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            dropdown_font=ctk.CTkFont(size=11)
        )
        self.repo_menu.grid(row=1, column=0, padx=(0, 8), pady=(4, 0))

        self.open_repo_btn = self._create_secondary_button(
            self.left_wrapper,
            text="Abrir",
            icon_name="repo.png",
            command=self.on_select_repo,
            width=84
        )
        self.open_repo_btn.grid(row=1, column=1, padx=(0, 10), pady=(4, 0))

        ctk.CTkLabel(
            self.left_wrapper,
            text="branch",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=10)
        ).grid(row=0, column=2, sticky="w", padx=(0, 4))

        self.branch_group = ctk.CTkFrame(self.left_wrapper, fg_color="transparent")
        self.branch_group.grid(row=1, column=2, sticky="w", pady=(4, 0))

        self.branch_menu = ctk.CTkOptionMenu(
            self.branch_group,
            values=["Nenhuma branch"],
            variable=self.branch_var,
            width=142,
            height=32,
            fg_color="#202631",
            button_color="#596273",
            button_hover_color="#697385",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            dropdown_font=ctk.CTkFont(size=11),
            command=self._handle_branch_menu_change,
            state="disabled"
        )
        self.branch_menu.pack(side="left", padx=(0, 8))

        self.refresh_btn = self._create_primary_icon_button(
            self.branch_group,
            icon_name="refresh.png",
            command=lambda: self.on_action("Refresh")
        )
        self.refresh_btn.pack(side="left")

    # =========================
    # CENTER
    # =========================
    def _build_center_section(self):
        self.center_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.center_wrapper.grid(row=0, column=1, sticky="nsew", padx=4, pady=6)

        self.toolbar_groups = [
            [("Undo", "undo.png"), ("Redo", "redo.png")],
            [
                ("Pull", "pull.png"),
                ("Push", "push.png"),
                ("Branch", "branch.png"),
                ("Delete Branch", "delete_branch.png"),
                ("Stash", "stash.png"),
                ("Pop", "pop.png")
            ],
            [
                ("Open PR", "open_pr.png"),
                ("Merge PR", "merge_pr.png"),
                ("Terminal", "terminal.png")],
        ]

        self._render_center_toolbar()

    def _render_center_toolbar(self):
        for child in self.center_wrapper.winfo_children():
            child.destroy()

        visible_actions = self._get_visible_center_actions()
        visible_groups = []

        for group in self.toolbar_groups:
            filtered_group = [item for item in group if item[0] in visible_actions]
            if filtered_group:
                visible_groups.append(filtered_group)

        for group_index, group in enumerate(visible_groups):
            group_frame = ctk.CTkFrame(self.center_wrapper, fg_color="transparent")
            group_frame.grid(row=0, column=group_index * 2, sticky="w")

            for index, (label, icon_name) in enumerate(group):
                button = self._create_toolbar_button(
                    group_frame,
                    text=label,
                    icon_name=icon_name,
                    command=lambda action=label: self.on_action(action),
                    width=self._get_toolbar_button_width(label)
                )
                button.grid(row=0, column=index, padx=2, pady=0)

            if group_index < len(visible_groups) - 1:
                sep = ctk.CTkFrame(
                    self.center_wrapper,
                    fg_color="#445064",
                    width=1,
                    height=22
                )
                sep.grid(row=0, column=(group_index * 2) + 1, padx=8, pady=5, sticky="ns")

    def _get_toolbar_button_width(self, label: str) -> int:
        compact_mode = self._size_mode == "small"

        if compact_mode:
            if label in {"Delete Branch"}:
                return 44
            if label in {"Open PR", "Merge PR", "Terminal"}:
                return 40
            return 38

        if label in {"Undo", "Redo"}:
            return 68
        if label in {"Pull", "Push", "Branch", "Stash", "Pop"}:
            return 72
        if label == "Delete Branch":
            return 108
        if label in {"Open PR", "Merge PR"}:
            return 88
        if label == "Terminal":
            return 82
        return 72

    def _get_visible_center_actions(self) -> list[str]:
        width = max(self.winfo_width(), 1)

        all_actions = [
            "Undo", "Redo",
            "Pull", "Push", "Branch", "Delete Branch", "Stash", "Pop",
            "Open PR", "Merge PR", "Terminal"
        ]

        if width >= 1500:
            self.hidden_actions = []
            return all_actions

        if width >= 1380:
            self.hidden_actions = ["Terminal"]
            return [a for a in all_actions if a not in self.hidden_actions]

        if width >= 1280:
            self.hidden_actions = ["Open PR", "Merge PR", "Terminal"]
            return [a for a in all_actions if a not in self.hidden_actions]

        if width >= 1180:
            self.hidden_actions = ["Delete Branch", "Open PR", "Merge PR", "Terminal"]
            return [a for a in all_actions if a not in self.hidden_actions]

        if width >= 1080:
            self.hidden_actions = ["Stash", "Pop", "Delete Branch", "Open PR", "Merge PR", "Terminal"]
            return [a for a in all_actions if a not in self.hidden_actions]

        self.hidden_actions = ["Branch", "Stash", "Pop", "Delete Branch", "Open PR", "Merge PR", "Terminal"]
        return [a for a in all_actions if a not in self.hidden_actions]

    # =========================
    # RIGHT
    # =========================
    def _build_right_section(self):
        self.right_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.right_wrapper.grid(row=0, column=2, sticky="e", padx=10, pady=6)

        self.actions_btn = self._create_secondary_button(
            self.right_wrapper,
            text="Actions",
            icon_name="actions.png",
            command=self._toggle_actions_popup,
            width=90
        )
        self.actions_btn.grid(row=0, column=0, padx=3, pady=0)

        self.search_btn = self._create_secondary_button(
            self.right_wrapper,
            text="Search",
            icon_name="search.png",
            command=lambda: self.on_action("Search"),
            width=78
        )
        self.search_btn.grid(row=0, column=1, padx=3, pady=0)

        self.profile_btn = self._create_secondary_button(
            self.right_wrapper,
            text="Profile",
            icon_name="profile.png",
            command=lambda: self.on_action("Profile"),
            width=82
        )
        self.profile_btn.grid(row=0, column=2, padx=3, pady=0)

    def _update_actions_button_label(self):
        if self.hidden_actions and self._size_mode != "small":
            self.actions_btn.configure(text=f"Actions ({len(self.hidden_actions)})")
        elif self._size_mode != "small":
            self.actions_btn.configure(text="Actions")

    def set_profile_label(self, text: str):
        if self._size_mode == "small":
            self.profile_btn.configure(text="")
        elif self._size_mode == "medium":
            self.profile_btn.configure(text="")
        else:
            self.profile_btn.configure(text=text)

    def _toggle_actions_popup(self):
        if self.actions_popup is not None and self.actions_popup.winfo_exists():
            self._close_actions_popup()
        else:
            self._open_actions_popup()

    def _open_actions_popup(self):
        self._close_actions_popup()

        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color="#111827")

        x = self.actions_btn.winfo_rootx()
        y = self.actions_btn.winfo_rooty() + self.actions_btn.winfo_height() + 6
        popup.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(
            popup,
            fg_color="#111827",
            corner_radius=10,
            border_width=1,
            border_color=APP_COLORS["border"]
        )
        container.pack(fill="both", expand=True, padx=1, pady=1)

        actions_to_show = self.hidden_actions[:] if self.hidden_actions else [
            "Actions", "Search", "Profile"
        ]

        for action in actions_to_show:
            btn = ctk.CTkButton(
                container,
                text=action,
                height=34,
                fg_color="transparent",
                hover_color="#374151",
                text_color=APP_COLORS["text"],
                anchor="w",
                corner_radius=8,
                font=ctk.CTkFont(size=11),
                command=lambda a=action: self._handle_popup_action(a)
            )
            btn.pack(fill="x", padx=8, pady=4)

        self.actions_popup = popup
        popup.bind("<FocusOut>", lambda _e: self._close_actions_popup())
        popup.focus_force()

    def _handle_popup_action(self, action_name: str):
        self._close_actions_popup()
        self.on_action(action_name)

    def _close_actions_popup(self):
        if self.actions_popup is not None and self.actions_popup.winfo_exists():
            self.actions_popup.destroy()
        self.actions_popup = None

    # =========================
    # RESPONSIVE
    # =========================
    def _schedule_responsive_update(self, _event=None):
        if self._responsive_job is not None:
            self.after_cancel(self._responsive_job)
        self._responsive_job = self.after(50, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        self._responsive_job = None

        width = max(self.winfo_width(), 1)

        if width >= 1450:
            self._size_mode = "large"
        elif width >= 1180:
            self._size_mode = "medium"
        else:
            self._size_mode = "small"

        self._apply_left_responsive()
        self._apply_right_responsive()
        self._render_center_toolbar()
        self._update_actions_button_label()

    def _apply_left_responsive(self):
        if self._size_mode == "large":
            self.repo_menu.configure(width=160)
            self.branch_menu.configure(width=142)
            self.open_repo_btn.configure(text="Abrir", width=84)
            self.grid_columnconfigure(0, minsize=360)
            return

        if self._size_mode == "medium":
            self.repo_menu.configure(width=138)
            self.branch_menu.configure(width=120)
            self.open_repo_btn.configure(text="Abrir", width=80)
            self.grid_columnconfigure(0, minsize=325)
            return

        self.repo_menu.configure(width=124)
        self.branch_menu.configure(width=108)
        self.open_repo_btn.configure(text="", width=36)
        self.grid_columnconfigure(0, minsize=290)

    def _apply_right_responsive(self):
        if self._size_mode == "large":
            self.actions_btn.configure(text="Actions", width=90)
            self.search_btn.configure(text="Search", width=78)
            self.profile_btn.configure(width=82)
            self.grid_columnconfigure(2, minsize=220)
            return

        if self._size_mode == "medium":
            self.actions_btn.configure(text="Actions", width=84)
            self.search_btn.configure(text="", width=36)
            self.profile_btn.configure(text="", width=36)
            self.grid_columnconfigure(2, minsize=168)
            return

        self.actions_btn.configure(text="", width=36)
        self.search_btn.configure(text="", width=36)
        self.profile_btn.configure(text="", width=36)
        self.grid_columnconfigure(2, minsize=128)

    # =========================
    # BUTTON HELPERS
    # =========================
    def _create_toolbar_button(self, master, text, icon_name, command, width=72):
        show_text = self._size_mode != "small"

        return ctk.CTkButton(
            master,
            text=text if show_text else "",
            image=load_icon(icon_name, size=(18, 18), padding=1),
            compound="left",
            anchor="center",
            width=width,
            height=34,
            command=command,
            fg_color="transparent",
            hover_color="#2e3948",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=6 if show_text else 0,
            font=ctk.CTkFont(size=11, weight="bold")
        )

    def _create_secondary_button(self, master, text, icon_name, command, width=80):
        return ctk.CTkButton(
            master,
            text=text,
            image=load_icon(icon_name, size=(16, 16), padding=1),
            compound="left",
            anchor="center",
            width=width,
            height=32,
            command=command,
            fg_color="#394454",
            hover_color="#465365",
            text_color=APP_COLORS["text"],
            corner_radius=8,
            border_width=0,
            border_spacing=6,
            font=ctk.CTkFont(size=11)
        )

    def _create_primary_icon_button(self, master, icon_name, command):
        return ctk.CTkButton(
            master,
            text="",
            image=load_icon(icon_name, size=(17, 17)),
            width=34,
            height=32,
            command=command,
            fg_color="#1d8fe1",
            hover_color="#2ea4f7",
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
