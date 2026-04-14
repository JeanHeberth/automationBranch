import customtkinter as ctk
from ui.theme import APP_COLORS


class CommitRow(ctk.CTkFrame):
    def __init__(self, master, branch_text: str, commit_text: str, selected: bool = False, is_head: bool = False):
        super().__init__(
            master,
            fg_color="#22314a" if selected else "transparent",
            corner_radius=6,
            height=44
        )

        self.grid_columnconfigure(0, weight=0, minsize=170)
        self.grid_columnconfigure(1, weight=0, minsize=120)
        self.grid_columnconfigure(2, weight=1)

        # BRANCH / TAG
        branch_frame = ctk.CTkFrame(self, fg_color="transparent")
        branch_frame.grid(row=0, column=0, sticky="nsew", padx=(6, 8), pady=4)

        if branch_text:
            badge = ctk.CTkFrame(
                branch_frame,
                fg_color="#0d7ea3" if selected else "#2a2f3a",
                corner_radius=6,
                height=28
            )
            badge.pack(side="left", padx=(0, 4))

            badge_label = ctk.CTkLabel(
                badge,
                text=branch_text,
                text_color="#f8fafc",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            badge_label.pack(padx=10, pady=4)

            if is_head:
                head = ctk.CTkFrame(
                    branch_frame,
                    fg_color="#2a2f3a",
                    corner_radius=6,
                    height=28,
                    width=38
                )
                head.pack(side="left", padx=(0, 4))
                head_label = ctk.CTkLabel(
                    head,
                    text="+2",
                    text_color=APP_COLORS["text"],
                    font=ctk.CTkFont(size=12, weight="bold")
                )
                head_label.pack(padx=8, pady=4)

        # GRAPH
        graph = ctk.CTkFrame(self, fg_color="transparent")
        graph.grid(row=0, column=1, sticky="ns", pady=0)

        canvas = ctk.CTkCanvas(
            graph,
            width=100,
            height=40,
            bg=APP_COLORS["panel"],
            highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)

        line_color = "#1ec8ff"
        node_fill = "#20c6f7"

        canvas.create_line(28, 0, 28, 40, fill=line_color, width=3)
        canvas.create_oval(19, 11, 37, 29, fill=node_fill, outline=node_fill)

        if selected:
            canvas.create_line(37, 20, 85, 20, fill=line_color, width=3)

        # COMMIT MESSAGE
        commit_label = ctk.CTkLabel(
            self,
            text=commit_text,
            text_color=APP_COLORS["text"],
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=13)
        )
        commit_label.grid(row=0, column=2, sticky="ew", padx=(8, 12), pady=8)


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

        header.grid_columnconfigure(0, weight=0, minsize=190)
        header.grid_columnconfigure(1, weight=0, minsize=120)
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
        ).grid(row=0, column=1, sticky="w", padx=(10, 8), pady=8)

        ctk.CTkLabel(
            header,
            text="COMMIT MESSAGE",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=2, sticky="w", padx=(10, 8), pady=8)

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

        for index, commit in enumerate(commits):
            branch_badge = self.current_branch if index == 0 and self.current_branch else ""
            row = CommitRow(
                self.scroll,
                branch_text=branch_badge,
                commit_text=commit,
                selected=(index == 0),
                is_head=(index == 0)
            )
            row.pack(fill="x", padx=8, pady=2)

    def _empty_state(self, text: str):
        ctk.CTkLabel(
            self.scroll,
            text=text,
            text_color=APP_COLORS["muted"]
        ).pack(pady=20)