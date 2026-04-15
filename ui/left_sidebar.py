import customtkinter as ctk
from ui.theme import APP_COLORS


class SidebarSection(ctk.CTkFrame):
    def __init__(self, master, title: str, count: str = "", expanded: bool = True, fonts: dict | None = None):
        super().__init__(master, fg_color="transparent")

        self.expanded = expanded
        self.fonts = fonts or {}

        self.header = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.header.pack(fill="x", padx=0, pady=(0, 3))

        self.arrow_label = ctk.CTkLabel(
            self.header,
            text="⌄" if expanded else "›",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=14, weight="bold"),
            width=16
        )
        self.arrow_label.pack(side="left", padx=(1, 5))

        self.title_label = ctk.CTkLabel(
            self.header,
            text=title,
            text_color=APP_COLORS["muted"],
            font=self.fonts.get("section")
        )
        self.title_label.pack(side="left")

        self.count_label = ctk.CTkLabel(
            self.header,
            text=count,
            text_color="#9bb1ff",
            font=self.fonts.get("section")
        )
        self.count_label.pack(side="right", padx=(5, 3))

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content.pack(fill="x", padx=0, pady=(0, 6))

        for widget in [self.header, self.arrow_label, self.title_label, self.count_label]:
            widget.bind("<Button-1>", self.toggle)

    def toggle(self, _event=None):
        self.expanded = not self.expanded
        self.arrow_label.configure(text="⌄" if self.expanded else "›")

        if self.expanded:
            self.content.pack(fill="x", padx=0, pady=(0, 6))
        else:
            self.content.pack_forget()


class SidebarItem(ctk.CTkFrame):
    def __init__(
        self,
        master,
        text: str,
        icon: str = "",
        level: int = 0,
        selected: bool = False,
        command=None,
        fonts: dict | None = None
    ):
        self.text_value = text
        self.level = level
        self.command = command
        self.selected = selected
        self.fonts = fonts or {}

        super().__init__(
            master,
            fg_color="#3c5f3e" if selected else "transparent",
            corner_radius=0,
            height=32
        )

        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True)

        pad_left = 10 + (level * 18)

        self.icon_label = ctk.CTkLabel(
            self.inner,
            text=icon,
            text_color="#d8dde6" if selected else APP_COLORS["muted"],
            font=ctk.CTkFont(size=12),
            width=18
        )
        self.icon_label.pack(side="left", padx=(pad_left, 6))

        self.text_label = ctk.CTkLabel(
            self.inner,
            text=text,
            text_color="#f8fafc" if selected else APP_COLORS["text"],
            font=self.fonts.get("item_selected") if selected else self.fonts.get("item"),
            anchor="w"
        )
        self.text_label.pack(side="left", fill="x", expand=True)

        for widget in [self, self.inner, self.icon_label, self.text_label]:
            widget.bind("<Button-1>", self._on_click)

    def _on_click(self, _event=None):
        if self.command:
            self.command(self.text_value)

    def set_selected(self, selected: bool):
        self.selected = selected
        self.configure(fg_color="#3c5f3e" if selected else "transparent")
        self.icon_label.configure(
            text_color="#d8dde6" if selected else APP_COLORS["muted"]
        )
        self.text_label.configure(
            text_color="#f8fafc" if selected else APP_COLORS["text"],
            font=self.fonts.get("item_selected") if selected else self.fonts.get("item")
        )


class LeftSidebar(ctk.CTkFrame):
    def __init__(self, master, on_branch_select=None, on_open_pr=None, on_merge_pr=None):
        super().__init__(
            master,
            fg_color=APP_COLORS["sidebar"],
            corner_radius=0,
            width=230
        )

        self.pack_propagate(False)

        self.on_branch_select = on_branch_select
        self.on_open_pr = on_open_pr
        self.on_merge_pr = on_merge_pr

        self.selected_branch = ""
        self.branch_items: dict[str, SidebarItem] = {}
        self.all_branches: list[str] = []
        self.remote_branches: list[str] = []
        self.remotes: list[str] = []
        self.pull_requests: list[dict] = []

        self.fonts = self._create_fonts()

        self._build_header()
        self._build_scroll_area()
        self._build_footer()

        self.set_branches([], remote_branches=[], remotes=[])

    def _create_fonts(self):
        return {
            "title": ctk.CTkFont(family="Helvetica Neue", size=14, weight="bold"),
            "section": ctk.CTkFont(family="Helvetica Neue", size=12, weight="bold"),
            "item": ctk.CTkFont(family="Helvetica Neue", size=12),
            "item_selected": ctk.CTkFont(family="Helvetica Neue", size=12, weight="bold"),
            "footer": ctk.CTkFont(family="Helvetica Neue", size=11),
            "search": ctk.CTkFont(family="Helvetica Neue", size=12),
            "pr": ctk.CTkFont(family="Helvetica Neue", size=11),
        }

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=82)
        header.pack(fill="x", padx=10, pady=(8, 6))

        top_line = ctk.CTkFrame(header, fg_color="transparent")
        top_line.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            top_line,
            text="◀",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            width=20
        ).pack(side="left", padx=(0, 4))

        self.viewing_label = ctk.CTkLabel(
            top_line,
            text="Viewing 0",
            text_color=APP_COLORS["text"],
            font=self.fonts["title"]
        )
        self.viewing_label.pack(side="left")

        search_row = ctk.CTkFrame(header, fg_color="transparent")
        search_row.pack(fill="x")

        self.search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Filter (⌘ + Option + f)",
            height=34,
            corner_radius=8,
            fg_color="#1b1f27",
            border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"],
            font=self.fonts["search"]
        )
        self.search_entry.pack(fill="x", side="left", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_filter_change)

        self.search_btn = ctk.CTkButton(
            search_row,
            text="⌕",
            width=30,
            height=34,
            fg_color="transparent",
            hover_color="#323846",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=14)
        )
        self.search_btn.pack(side="left", padx=(4, 0))

        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=0, pady=(0, 3))

    def _build_scroll_area(self):
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

    def _build_footer(self):
        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=0, pady=(0, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent", height=40)
        footer.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkLabel(
            footer,
            text="🚀",
            text_color="#6ee7a8",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=(4, 6))

        self.footer_label = ctk.CTkLabel(
            footer,
            text="Nenhum repositório selecionado",
            text_color=APP_COLORS["text"],
            font=self.fonts["footer"],
            anchor="w"
        )
        self.footer_label.pack(side="left", fill="x", expand=True)

    def _clear_sections(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.branch_items.clear()

    def _section_divider(self):
        ctk.CTkFrame(
            self.scroll,
            fg_color=APP_COLORS["border"],
            height=1
        ).pack(fill="x", padx=0, pady=(0, 8))

    def _render_local_section(self, branches: list[str]):
        local = SidebarSection(self.scroll, "LOCAL", str(len(branches)), expanded=True, fonts=self.fonts)
        local.pack(fill="x", padx=0, pady=(3, 8))

        if not branches:
            ctk.CTkLabel(
                local.content,
                text="Nenhuma branch local",
                text_color=APP_COLORS["muted"],
                font=self.fonts["item"]
            ).pack(anchor="w", padx=14, pady=(2, 6))
            return

        for branch in branches:
            item = SidebarItem(
                local.content,
                branch,
                icon="⑂",
                level=0,
                selected=(branch == self.selected_branch),
                command=self._handle_branch_click,
                fonts=self.fonts
            )
            item.pack(fill="x")
            self.branch_items[branch] = item

    def _render_remote_section(self, remote_branches: list[str], remotes: list[str]):
        remote = SidebarSection(self.scroll, "REMOTE", str(len(remotes)), expanded=True, fonts=self.fonts)
        remote.pack(fill="x", padx=0, pady=(0, 8))

        if not remotes:
            ctk.CTkLabel(
                remote.content,
                text="Nenhum remote",
                text_color=APP_COLORS["muted"],
                font=self.fonts["item"]
            ).pack(anchor="w", padx=14, pady=(2, 6))
            return

        for remote_name in remotes:
            SidebarItem(
                remote.content,
                remote_name,
                icon="☁",
                level=0,
                fonts=self.fonts
            ).pack(fill="x")

            related = []
            prefix = f"{remote_name}/"
            for branch in remote_branches:
                if branch.startswith(prefix):
                    related.append(branch[len(prefix):])

            if not related:
                ctk.CTkLabel(
                    remote.content,
                    text="Nenhuma branch remota",
                    text_color=APP_COLORS["muted"],
                    font=self.fonts["item"]
                ).pack(anchor="w", padx=30, pady=(2, 6))
                continue

            for branch_name in related:
                SidebarItem(
                    remote.content,
                    branch_name,
                    icon="⑂",
                    level=1,
                    fonts=self.fonts
                ).pack(fill="x")

    def _render_pull_requests_section(self):
        prs = SidebarSection(
            self.scroll,
            "PULL REQUESTS",
            str(len(self.pull_requests)),
            expanded=True if self.pull_requests else False,
            fonts=self.fonts
        )
        prs.pack(fill="x", padx=0, pady=(0, 5))

        if not self.pull_requests:
            ctk.CTkLabel(
                prs.content,
                text="Nenhum PR aberto",
                text_color=APP_COLORS["muted"],
                font=self.fonts["pr"]
            ).pack(anchor="w", padx=14, pady=(2, 6))
            return

        for pr in self.pull_requests:
            title = f"#{pr.get('number')} {pr.get('title', '')}"
            head = pr.get("head", "")
            base = pr.get("base", "")

            item = ctk.CTkFrame(prs.content, fg_color="#2a2f3a", corner_radius=8)
            item.pack(fill="x", padx=6, pady=3)

            ctk.CTkLabel(
                item,
                text=title,
                text_color=APP_COLORS["text"],
                font=self.fonts["pr"],
                anchor="w",
                justify="left",
                wraplength=180
            ).pack(fill="x", padx=8, pady=(6, 2))

            ctk.CTkLabel(
                item,
                text=f"{head} → {base}",
                text_color=APP_COLORS["muted"],
                font=ctk.CTkFont(size=10),
                anchor="w"
            ).pack(fill="x", padx=8, pady=(0, 5))

            actions_row = ctk.CTkFrame(item, fg_color="transparent")
            actions_row.pack(fill="x", padx=6, pady=(0, 6))

            open_btn = ctk.CTkButton(
                actions_row,
                text="Abrir",
                width=58,
                height=26,
                fg_color="#2563EB",
                hover_color="#3B82F6",
                text_color="#FFFFFF",
                corner_radius=7,
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda p=pr: self._handle_open_pr_click(p)
            )
            open_btn.pack(side="left", padx=(0, 5))

            merge_btn = ctk.CTkButton(
                actions_row,
                text="Merge",
                width=58,
                height=26,
                fg_color="#374151",
                hover_color="#4B5563",
                text_color=APP_COLORS["text"],
                corner_radius=7,
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda p=pr: self._handle_merge_pr_click(p)
            )
            merge_btn.pack(side="left")

    def _handle_open_pr_click(self, pr: dict):
        if self.on_open_pr:
            self.on_open_pr(pr)

    def _handle_merge_pr_click(self, pr: dict):
        if self.on_merge_pr:
            self.on_merge_pr(pr)

    def _build_static_sections(self):
        self._section_divider()
        self._render_remote_section(self.remote_branches, self.remotes)

        self._section_divider()
        cloud = SidebarSection(self.scroll, "CLOUD PATCHES", "0", expanded=True, fonts=self.fonts)
        cloud.pack(fill="x", padx=0, pady=(0, 8))

        self._section_divider()
        self._render_pull_requests_section()

        self._section_divider()
        issues = SidebarSection(self.scroll, "ISSUES", "", expanded=False, fonts=self.fonts)
        issues.pack(fill="x", padx=0, pady=(0, 5))

        self._section_divider()
        teams = SidebarSection(self.scroll, "TEAMS", "", expanded=False, fonts=self.fonts)
        teams.pack(fill="x", padx=0, pady=(0, 5))

    def _render_branches(self, branches: list[str]):
        self._clear_sections()
        self._render_local_section(branches)
        self._build_static_sections()
        self.set_viewing_count(len(branches))

    def _handle_branch_click(self, branch_name: str):
        self.selected_branch = branch_name

        for name, item in self.branch_items.items():
            item.set_selected(name == branch_name)

        self.set_footer_message(f"Branch selecionada: {branch_name}")

        if self.on_branch_select:
            self.on_branch_select(branch_name)

    def _on_filter_change(self, _event=None):
        term = self.search_entry.get().strip().lower()

        if not term:
            filtered = self.all_branches
        else:
            filtered = [b for b in self.all_branches if term in b.lower()]

        self._render_branches(filtered)

    def set_branches(self, branches: list[str], remote_branches: list[str] | None = None, remotes: list[str] | None = None):
        self.all_branches = branches[:] if branches else []
        self.remote_branches = remote_branches[:] if remote_branches else []
        self.remotes = remotes[:] if remotes else []

        if self.selected_branch not in self.all_branches:
            self.selected_branch = self.all_branches[0] if self.all_branches else ""

        self._render_branches(self.all_branches)

    def set_pull_requests(self, pull_requests: list[dict]):
        self.pull_requests = pull_requests[:] if pull_requests else []
        self._render_branches(self.all_branches)

    def set_selected_branch(self, branch_name: str):
        self.selected_branch = branch_name

        for name, item in self.branch_items.items():
            item.set_selected(name == branch_name)

    def set_footer_message(self, message: str):
        self.footer_label.configure(text=message)

    def set_viewing_count(self, count: int):
        self.viewing_label.configure(text=f"Viewing {count}")