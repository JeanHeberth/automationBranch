import customtkinter as ctk
from ui.theme import APP_COLORS


class CommitRow(ctk.CTkFrame):
    def __init__(self, master, branch_text: str, commit_text: str, selected: bool = False, is_head: bool = False):
        super().__init__(
            master,
            fg_color="#192438" if selected else "transparent",
            corner_radius=6,
            height=42
        )

        self.grid_columnconfigure(0, weight=0, minsize=150)
        self.grid_columnconfigure(1, weight=0, minsize=92)
        self.grid_columnconfigure(2, weight=1)

        # BRANCH / TAG
        branch_frame = ctk.CTkFrame(self, fg_color="transparent")
        branch_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=4)

        if branch_text:
            badge = ctk.CTkFrame(
                branch_frame,
                fg_color="#108bb8" if selected else "#2a2f3a",
                corner_radius=6,
                height=26
            )
            badge.pack(side="left", padx=(0, 4))

            badge_label = ctk.CTkLabel(
                badge,
                text=branch_text,
                text_color="#f8fafc",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            badge_label.pack(padx=10, pady=3)

            if is_head:
                head = ctk.CTkFrame(
                    branch_frame,
                    fg_color="#2a2f3a",
                    corner_radius=6,
                    height=26
                )
                head.pack(side="left", padx=(0, 4))

                head_label = ctk.CTkLabel(
                    head,
                    text="+2",
                    text_color=APP_COLORS["text"],
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                head_label.pack(padx=8, pady=3)

        # GRAPH
        graph = ctk.CTkFrame(self, fg_color="transparent")
        graph.grid(row=0, column=1, sticky="ns", pady=0)

        canvas = ctk.CTkCanvas(
            graph,
            width=90,
            height=38,
            bg=APP_COLORS["panel"],
            highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)

        line_color = "#1ec8ff"
        node_fill = "#20c6f7"

        center_x = 26
        center_y = 19
        node_radius = 8

        canvas.create_line(center_x, 0, center_x, 38, fill=line_color, width=3)
        canvas.create_oval(
            center_x - node_radius,
            center_y - node_radius,
            center_x + node_radius,
            center_y + node_radius,
            fill=node_fill,
            outline=node_fill
        )

        if selected:
            canvas.create_line(center_x + node_radius, center_y, 86, center_y, fill=line_color, width=3)

        # COMMIT MESSAGE
        commit_label = ctk.CTkLabel(
            self,
            text=commit_text,
            text_color=APP_COLORS["text"],
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=13)
        )
        commit_label.grid(row=0, column=2, sticky="ew", padx=(6, 12), pady=8)


class CenterPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0
        )

        self.current_branch = ""
        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#2a2f3a", corner_radius=0, height=38)
        header.pack(fill="x", padx=0, pady=(0, 6))

        header.grid_columnconfigure(0, weight=0, minsize=160)
        header.grid_columnconfigure(1, weight=0, minsize=100)
        header.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            header,
            text="BRANCH / TAG",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=(14, 8), pady=8)

        ctk.CTkLabel(
            header,
            text="GRAPH",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=1, sticky="w", padx=(8, 8), pady=8)

        ctk.CTkLabel(
            header,
            text="COMMIT MESSAGE",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=2, sticky="w", padx=(8, 8), pady=8)

    def _build_body(self):
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

    def clear(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

    def set_current_branch(self, branch_name: str):
        self.current_branch = branch_name

    def set_commits(self, commits: list[str]):
        self.clear()

        if not commits:
            self._empty_state("Nenhum commit encontrado.")
            return

        if not self.current_branch:
            self._empty_state(commits[0] if commits else "Nenhum repositório selecionado.")
            return

        for index, commit in enumerate(commits):
            branch_badge = self.current_branch if index == 0 else ""
            row = CommitRow(
                self.scroll,
                branch_text=branch_badge,
                commit_text=commit,
                selected=(index == 0),
                is_head=(index == 0)
            )
            row.pack(fill="x", padx=8, pady=2)

    def _empty_state(self, text: str):
        container = ctk.CTkFrame(
            self.scroll,
            fg_color="transparent"
        )
        container.pack(fill="both", expand=True, padx=20, pady=30)

        label = ctk.CTkLabel(
            container,
            text=text,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=14),
            anchor="center",
            justify="center"
        )
        label.pack(expand=True, pady=40)