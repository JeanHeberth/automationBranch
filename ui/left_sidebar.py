import customtkinter as ctk
from ui.theme import APP_COLORS


class SidebarSection(ctk.CTkFrame):
    def __init__(self, master, title: str, count: str = "", expanded: bool = True):
        super().__init__(master, fg_color="transparent")

        self.title = title
        self.count = count
        self.expanded = expanded

        self.header = ctk.CTkFrame(self, fg_color="transparent", height=34)
        self.header.pack(fill="x", padx=0, pady=(0, 4))

        arrow = "⌄" if expanded else "›"
        self.arrow_label = ctk.CTkLabel(
            self.header,
            text=arrow,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=16, weight="bold"),
            width=18
        )
        self.arrow_label.pack(side="left", padx=(2, 6))

        self.title_label = ctk.CTkLabel(
            self.header,
            text=title,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.title_label.pack(side="left")

        self.count_label = ctk.CTkLabel(
            self.header,
            text=count,
            text_color="#9bb1ff",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.count_label.pack(side="right", padx=(6, 4))

        self.content = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content.pack(fill="x", padx=0, pady=(0, 8))

        self.header.bind("<Button-1>", self.toggle)
        self.arrow_label.bind("<Button-1>", self.toggle)
        self.title_label.bind("<Button-1>", self.toggle)
        self.count_label.bind("<Button-1>", self.toggle)

    def toggle(self, _event=None):
        self.expanded = not self.expanded
        self.arrow_label.configure(text="⌄" if self.expanded else "›")

        if self.expanded:
            self.content.pack(fill="x", padx=0, pady=(0, 8))
        else:
            self.content.pack_forget()

    def set_count(self, value: str):
        self.count_label.configure(text=value)


class SidebarItem(ctk.CTkFrame):
    def __init__(
        self,
        master,
        text: str,
        icon: str = "",
        level: int = 0,
        selected: bool = False,
        command=None
    ):
        bg_color = "#3c5f3e" if selected else "transparent"

        super().__init__(
            master,
            fg_color=bg_color,
            corner_radius=0,
            height=36
        )

        self.command = command
        self.selected = selected

        pad_left = 14 + (level * 22)

        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="both", expand=True, padx=0, pady=0)

        self.icon_label = ctk.CTkLabel(
            self.inner,
            text=icon,
            text_color="#d8dde6" if selected else APP_COLORS["muted"],
            font=ctk.CTkFont(size=14),
            width=24
        )
        self.icon_label.pack(side="left", padx=(pad_left, 8))

        self.text_label = ctk.CTkLabel(
            self.inner,
            text=text,
            text_color="#f1f5f9" if selected else APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold" if selected else "normal"),
            anchor="w"
        )
        self.text_label.pack(side="left", fill="x", expand=True)

        self.bind("<Button-1>", self._on_click)
        self.inner.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.text_label.bind("<Button-1>", self._on_click)

    def _on_click(self, _event=None):
        if self.command:
            self.command()


class LeftSidebar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["sidebar"],
            corner_radius=0,
            width=280
        )

        self.pack_propagate(False)

        self.selected_branch = "adfasdsaf"

        self._build_header()
        self._build_scroll_area()
        self._build_footer()

        self.populate_demo()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=96)
        header.pack(fill="x", padx=12, pady=(10, 8))

        top_line = ctk.CTkFrame(header, fg_color="transparent")
        top_line.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top_line,
            text="◀",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=16, weight="bold"),
            width=24
        ).pack(side="left", padx=(0, 4))

        self.viewing_label = ctk.CTkLabel(
            top_line,
            text="Viewing 4",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.viewing_label.pack(side="left")

        search_row = ctk.CTkFrame(header, fg_color="transparent")
        search_row.pack(fill="x")

        self.search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Filter (⌘ + Option + f)",
            height=36,
            corner_radius=8,
            fg_color="#1b1f27",
            border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"]
        )
        self.search_entry.pack(fill="x", side="left", expand=True)

        self.search_btn = ctk.CTkButton(
            search_row,
            text="⌕",
            width=36,
            height=36,
            fg_color="transparent",
            hover_color="#323846",
            text_color=APP_COLORS["muted"]
        )
        self.search_btn.pack(side="left", padx=(6, 0))

        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=0, pady=(0, 4))

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

        footer = ctk.CTkFrame(self, fg_color="transparent", height=48)
        footer.pack(fill="x", padx=8, pady=(6, 10))

        ctk.CTkLabel(
            footer,
            text="🚀",
            text_color="#6ee7a8",
            font=ctk.CTkFont(size=16)
        ).pack(side="left", padx=(6, 8))

        self.footer_label = ctk.CTkLabel(
            footer,
            text="JeanHeberth/swaglabsMobile#8 is ready to merge",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.footer_label.pack(side="left", fill="x", expand=True)

    def clear_sections(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

    def populate_demo(self):
        self.clear_sections()

        local = SidebarSection(self.scroll, "LOCAL", "3", expanded=True)
        local.pack(fill="x", padx=0, pady=(4, 10))

        SidebarItem(local.content, "feature", icon="▾", level=0).pack(fill="x")
        SidebarItem(
            local.content,
            "adfasdsaf",
            icon="⑂",
            level=1,
            selected=True
        ).pack(fill="x")
        SidebarItem(local.content, "main", icon="⑂", level=1).pack(fill="x")
        SidebarItem(local.content, "testando_kraken", icon="⑂", level=1).pack(fill="x")

        self._section_divider()

        remote = SidebarSection(self.scroll, "REMOTE", "1", expanded=True)
        remote.pack(fill="x", padx=0, pady=(0, 10))

        SidebarItem(remote.content, "origin", icon="☁", level=0).pack(fill="x")
        SidebarItem(remote.content, "main", icon="⑂", level=1).pack(fill="x")

        self._section_divider()

        cloud = SidebarSection(self.scroll, "CLOUD PATCHES", "0", expanded=True)
        cloud.pack(fill="x", padx=0, pady=(0, 10))

        self._section_divider()

        prs = SidebarSection(self.scroll, "PULL REQUESTS", "0", expanded=False)
        prs.pack(fill="x", padx=0, pady=(0, 6))

        self._section_divider()

        issues = SidebarSection(self.scroll, "ISSUES", "", expanded=False)
        issues.pack(fill="x", padx=0, pady=(0, 6))

        self._section_divider()

        teams = SidebarSection(self.scroll, "TEAMS", "", expanded=False)
        teams.pack(fill="x", padx=0, pady=(0, 6))

    def _section_divider(self):
        ctk.CTkFrame(
            self.scroll,
            fg_color=APP_COLORS["border"],
            height=1
        ).pack(fill="x", padx=0, pady=(0, 10))

    def set_branches(self, branches: list[str]):
        self.clear_sections()

        local = SidebarSection(self.scroll, "LOCAL", str(len(branches)), expanded=True)
        local.pack(fill="x", padx=0, pady=(4, 10))

        for branch in branches:
            selected = branch == self.selected_branch
            SidebarItem(
                local.content,
                branch,
                icon="⑂",
                level=0,
                selected=selected
            ).pack(fill="x")

        self._section_divider()

        remote = SidebarSection(self.scroll, "REMOTE", "1", expanded=True)
        remote.pack(fill="x", padx=0, pady=(0, 10))
        SidebarItem(remote.content, "origin", icon="☁", level=0).pack(fill="x")
        SidebarItem(remote.content, "main", icon="⑂", level=1).pack(fill="x")

        self._section_divider()

        cloud = SidebarSection(self.scroll, "CLOUD PATCHES", "0", expanded=True)
        cloud.pack(fill="x", padx=0, pady=(0, 10))

        self._section_divider()

        prs = SidebarSection(self.scroll, "PULL REQUESTS", "0", expanded=False)
        prs.pack(fill="x", padx=0, pady=(0, 6))

        self._section_divider()

        issues = SidebarSection(self.scroll, "ISSUES", "", expanded=False)
        issues.pack(fill="x", padx=0, pady=(0, 6))

        self._section_divider()

        teams = SidebarSection(self.scroll, "TEAMS", "", expanded=False)
        teams.pack(fill="x", padx=0, pady=(0, 6))

    def set_footer_message(self, message: str):
        self.footer_label.configure(text=message)

    def set_viewing_count(self, count: int):
        self.viewing_label.configure(text=f"Viewing {count}")