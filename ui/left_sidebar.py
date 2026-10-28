import sys
import tkinter as tk

import customtkinter as ctk
from ui.theme import APP_COLORS


class SidebarSection(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        count: str = "",
        expanded: bool = True,
        fonts: dict | None = None,
        lazy_fill=None,
        on_toggle=None,
    ):
        super().__init__(master, fg_color="transparent")

        self.expanded = expanded
        self.fonts = fonts or {}
        # lazy_fill: monta o conteúdo só na primeira vez que a seção é exibida
        # (evita criar centenas de widgets de uma seção que está recolhida).
        self._lazy_fill = lazy_fill
        self._on_toggle = on_toggle

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
            self._fill_if_needed()
            self.content.pack(fill="x", padx=0, pady=(0, 6))

        for widget in [self.header, self.arrow_label, self.title_label, self.count_label]:
            widget.bind("<Button-1>", self.toggle)

    def _fill_if_needed(self):
        if self._lazy_fill is not None:
            fill, self._lazy_fill = self._lazy_fill, None
            fill(self.content)

    def toggle(self, _event=None):
        self.expanded = not self.expanded
        self.arrow_label.configure(text="⌄" if self.expanded else "›")

        if self.expanded:
            self._fill_if_needed()
            self.content.pack(fill="x", padx=0, pady=(0, 6))
        else:
            self.content.pack_forget()

        if self._on_toggle:
            self._on_toggle(self.expanded)


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


# Atalho para focar o filtro: ⌘+Option+F no macOS, Ctrl+Alt+F no Windows/Linux.
if sys.platform == "darwin":
    FILTER_SHORTCUT_LABEL = "⌘ + Option + f"
    FILTER_SHORTCUT_SEQUENCE = "<Command-Option-f>"
else:
    FILTER_SHORTCUT_LABEL = "Ctrl + Alt + f"
    FILTER_SHORTCUT_SEQUENCE = "<Control-Alt-f>"


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
        # Estado de merge de cada PR (number -> {"state", "label", "auto_merge"}) e PRs
        # que o app está acompanhando para mergear sozinho quando os checks passarem.
        self.pr_statuses: dict[int, dict] = {}
        self.pr_watching: set[int] = set()

        # O que está desenhado hoje: permite pular redesenhos idênticos (muito caro no Windows).
        self._rendered_local: list[str] | None = None
        self._rendered_remote: tuple | None = None
        self._rendered_prs: tuple | None = None
        self._remote_expanded = False
        self._filter_job = None

        self.fonts = self._create_fonts()

        self._build_header()
        self._build_scroll_area()
        self._build_footer()

        self.set_branches([], remote_branches=[], remotes=[])

    def _focus_filter(self, _event=None):
        self.search_entry.focus_set()
        return "break"

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
            placeholder_text=f"Filter ({FILTER_SHORTCUT_LABEL})",
            height=34,
            corner_radius=8,
            fg_color="#1b1f27",
            border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"],
            font=self.fonts["search"]
        )
        self.search_entry.pack(fill="x", side="left", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_filter_change)
        self.winfo_toplevel().bind(FILTER_SHORTCUT_SEQUENCE, self._focus_filter, add="+")

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
        self._build_sections()

    def _new_box(self):
        box = ctk.CTkFrame(self.scroll, fg_color="transparent")
        box.pack(fill="x")
        return box

    def _build_sections(self):
        """Cria uma vez os contêineres; cada seção dinâmica é redesenhada de forma independente."""
        self.local_box = self._new_box()

        self._section_divider()
        self.remote_box = self._new_box()

        self._section_divider()
        cloud = SidebarSection(self.scroll, "CLOUD PATCHES", "0", expanded=True, fonts=self.fonts)
        cloud.pack(fill="x", padx=0, pady=(0, 8))

        self._section_divider()
        self.pr_box = self._new_box()

        self._section_divider()
        SidebarSection(self.scroll, "ISSUES", "", expanded=False, fonts=self.fonts).pack(
            fill="x", padx=0, pady=(0, 5)
        )

        self._section_divider()
        SidebarSection(self.scroll, "TEAMS", "", expanded=False, fonts=self.fonts).pack(
            fill="x", padx=0, pady=(0, 5)
        )

    @staticmethod
    def _clear_box(box):
        for widget in box.winfo_children():
            widget.destroy()

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

    def _section_divider(self):
        ctk.CTkFrame(
            self.scroll,
            fg_color=APP_COLORS["border"],
            height=1
        ).pack(fill="x", padx=0, pady=(0, 8))

    def _render_local_section(self, branches: list[str]):
        self._clear_box(self.local_box)
        self.branch_items.clear()
        self._rendered_local = branches[:]

        local = SidebarSection(self.local_box, "LOCAL", str(len(branches)), expanded=True, fonts=self.fonts)
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
        self._clear_box(self.remote_box)
        self._rendered_remote = (tuple(remote_branches), tuple(remotes))

        remote = SidebarSection(
            self.remote_box,
            "REMOTE",
            str(len(remotes)),
            expanded=self._remote_expanded,
            fonts=self.fonts,
            lazy_fill=lambda content: self._fill_remote_section(content, remote_branches, remotes),
            on_toggle=self._set_remote_expanded,
        )
        remote.pack(fill="x", padx=0, pady=(0, 8))

    def _set_remote_expanded(self, expanded: bool):
        self._remote_expanded = expanded

    def _fill_remote_section(self, parent, remote_branches: list[str], remotes: list[str]):
        if not remotes:
            ctk.CTkLabel(
                parent,
                text="Nenhum remote",
                text_color=APP_COLORS["muted"],
                font=self.fonts["item"]
            ).pack(anchor="w", padx=14, pady=(2, 6))
            return

        for remote_name in remotes:
            SidebarItem(
                parent,
                remote_name,
                icon="☁",
                level=0,
                fonts=self.fonts
            ).pack(fill="x")

            prefix = f"{remote_name}/"
            related = [b[len(prefix):] for b in remote_branches if b.startswith(prefix)]

            if not related:
                ctk.CTkLabel(
                    parent,
                    text="Nenhuma branch remota",
                    text_color=APP_COLORS["muted"],
                    font=self.fonts["item"]
                ).pack(anchor="w", padx=30, pady=(2, 6))
                continue

            # Uma branch remota é só texto: um tk.Label leve no lugar de 4 widgets do CustomTkinter.
            for branch_name in related:
                tk.Label(
                    parent,
                    text=f"⑂  {branch_name}",
                    anchor="w",
                    fg=APP_COLORS["text"],
                    bg=APP_COLORS["sidebar"],
                    font=self.fonts["item"],
                    padx=28,
                    pady=5,
                ).pack(fill="x")

    def _pr_signature(self):
        numbers = {pr.get("number") for pr in self.pull_requests}
        statuses = {
            n: (st.get("state"), st.get("label"), st.get("auto_merge"))
            for n, st in self.pr_statuses.items()
            if n in numbers
        }
        return [dict(pr) for pr in self.pull_requests], statuses, frozenset(self.pr_watching & numbers)

    def _pr_merge_button_spec(self, number, status: dict | None) -> tuple[str, bool, str, str]:
        """(texto, habilitado, cor, cor no hover) do botão de merge de um PR."""
        if number in self.pr_watching:
            return "Cancelar", True, "#B45309", "#D97706"

        if status is None:
            return "Merge", True, "#374151", "#4B5563"

        state = status.get("state")
        if state == "ready":
            return "Merge", True, "#16A34A", "#22C55E"
        if state == "pending":
            if status.get("auto_merge"):
                return "Auto ativo", False, "#1F2937", "#1F2937"
            return "Auto-merge", True, "#374151", "#4B5563"
        if state == "behind":
            return "Atualizar", True, "#C2410C", "#EA580C"

        return "Merge", False, "#1F2937", "#1F2937"

    def _render_pull_requests_section(self):
        self._clear_box(self.pr_box)
        self._rendered_prs = self._pr_signature()

        prs = SidebarSection(
            self.pr_box,
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
            ).pack(fill="x", padx=8, pady=(0, 3))

            status = self.pr_statuses.get(pr.get("number"))
            if status:
                label = status.get("label", "")
                if pr.get("number") in self.pr_watching:
                    label += " · merge automático (app aberto)"
                elif status.get("auto_merge"):
                    label += " · auto-merge ativo"

                ctk.CTkLabel(
                    item,
                    text=f"●  {label}",
                    text_color=self.PR_STATE_COLORS.get(status.get("state"), APP_COLORS["muted"]),
                    font=ctk.CTkFont(size=10),
                    anchor="w",
                    justify="left",
                    wraplength=180
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

            merge_text, merge_enabled, merge_color, merge_hover = self._pr_merge_button_spec(
                pr.get("number"), status
            )
            merge_btn = ctk.CTkButton(
                actions_row,
                text=merge_text,
                width=80,
                height=26,
                fg_color=merge_color,
                hover_color=merge_hover,
                text_color=APP_COLORS["text"] if merge_enabled else APP_COLORS["muted"],
                corner_radius=7,
                font=ctk.CTkFont(size=10, weight="bold"),
                state="normal" if merge_enabled else "disabled",
                command=lambda p=pr: self._handle_merge_pr_click(p)
            )
            merge_btn.pack(side="left")

    PR_STATE_COLORS = {
        "ready": "#22C55E",
        "pending": "#EAB308",
        "failed": "#EF4444",
        "conflict": "#EF4444",
        "behind": "#F97316",
        "blocked": "#9CA3AF",
    }

    def _handle_open_pr_click(self, pr: dict):
        if self.on_open_pr:
            self.on_open_pr(pr)

    def _handle_merge_pr_click(self, pr: dict):
        if self.on_merge_pr:
            self.on_merge_pr(pr)

    def _render_branches(self, branches: list[str]):
        """Redesenha só a seção LOCAL (usada pelo filtro e por mudanças nas branches locais)."""
        self._render_local_section(branches)
        self.set_viewing_count(len(branches))

    def _handle_branch_click(self, branch_name: str):
        self.selected_branch = branch_name

        for name, item in self.branch_items.items():
            item.set_selected(name == branch_name)

        self.set_footer_message(f"Branch selecionada: {branch_name}")

        if self.on_branch_select:
            self.on_branch_select(branch_name)

    def _on_filter_change(self, _event=None):
        # Espera o usuário parar de digitar antes de redesenhar a lista.
        if self._filter_job is not None:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(200, self._apply_filter)

    def _apply_filter(self):
        self._filter_job = None
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

        # Só redesenha o que mudou (num Refresh sem novidades nada é recriado).
        if self._rendered_local != self.all_branches:
            self._render_branches(self.all_branches)
        else:
            self.set_selected_branch(self.selected_branch)

        remote_key = (tuple(self.remote_branches), tuple(self.remotes))
        if self._rendered_remote != remote_key:
            self._render_remote_section(self.remote_branches, self.remotes)

        if self._rendered_prs is None:
            self._render_pull_requests_section()

    def set_pull_requests(self, pull_requests: list[dict]):
        self.pull_requests = pull_requests[:] if pull_requests else []

        if self._rendered_prs == self._pr_signature():
            return

        self._render_pull_requests_section()

    def set_pull_request_statuses(self, statuses: dict[int, dict], watching: set[int] | None = None):
        self.pr_statuses = dict(statuses)
        self.pr_watching = set(watching or ())

        if self._rendered_prs == self._pr_signature():
            return

        self._render_pull_requests_section()

    def set_selected_branch(self, branch_name: str):
        self.selected_branch = branch_name

        for name, item in self.branch_items.items():
            item.set_selected(name == branch_name)

    def set_footer_message(self, message: str):
        self.footer_label.configure(text=message)

    def set_viewing_count(self, count: int):
        self.viewing_label.configure(text=f"Viewing {count}")