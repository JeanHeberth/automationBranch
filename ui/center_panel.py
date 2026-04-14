import customtkinter as ctk
from ui.theme import APP_COLORS


GRAPH_COLORS = [
    "#1ec8ff",
    "#2d7cff",
    "#9b5cff",
    "#f59e0b",
    "#22c55e",
    "#ef4444",
    "#14b8a6",
    "#e879f9",
]


class CommitRow(ctk.CTkFrame):
    ROW_HEIGHT = 34
    GRAPH_WIDTH = 150

    def __init__(self, master, branch_text: str, commit_data: dict, selected: bool = False, is_head: bool = False):
        super().__init__(
            master,
            fg_color="#16243a" if selected else "transparent",
            corner_radius=0,
            height=self.ROW_HEIGHT
        )

        self.pack_propagate(False)
        self.grid_propagate(False)

        self.commit_data = commit_data
        self.selected = selected
        self.is_head = is_head

        self.grid_columnconfigure(0, weight=0, minsize=170)
        self.grid_columnconfigure(1, weight=0, minsize=self.GRAPH_WIDTH)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_branch_tag(branch_text)
        self._build_graph()
        self._build_commit_message()

    def _build_branch_tag(self, branch_text: str):
        branch_frame = ctk.CTkFrame(self, fg_color="transparent", height=self.ROW_HEIGHT)
        branch_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=0)
        branch_frame.pack_propagate(False)

        if not branch_text:
            return

        badge = ctk.CTkFrame(
            branch_frame,
            fg_color="#108bb8",
            corner_radius=6,
            height=26
        )
        badge.pack(side="left", padx=(0, 4), pady=4)

        badge_label = ctk.CTkLabel(
            badge,
            text=branch_text,
            text_color="#f8fafc",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        badge_label.pack(padx=10, pady=3)

        if self.is_head:
            extra = ctk.CTkFrame(
                branch_frame,
                fg_color="#2a2f3a",
                corner_radius=6,
                height=26
            )
            extra.pack(side="left", padx=(0, 4), pady=4)

            extra_label = ctk.CTkLabel(
                extra,
                text="+2",
                text_color=APP_COLORS["text"],
                font=ctk.CTkFont(size=12, weight="bold")
            )
            extra_label.pack(padx=8, pady=3)

    def _build_graph(self):
        graph_frame = ctk.CTkFrame(self, fg_color="transparent", height=self.ROW_HEIGHT)
        graph_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        graph_frame.pack_propagate(False)

        self.canvas = ctk.CTkCanvas(
            graph_frame,
            width=self.GRAPH_WIDTH,
            height=self.ROW_HEIGHT,
            bg=APP_COLORS["panel"],
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self._draw_graph(self.commit_data.get("graph", ""))

    def _build_commit_message(self):
        message_frame = ctk.CTkFrame(
            self,
            fg_color="#0f2b57" if self.selected else "transparent",
            corner_radius=6,
            height=self.ROW_HEIGHT
        )
        message_frame.grid(row=0, column=2, sticky="nsew", padx=(6, 10), pady=0)
        message_frame.pack_propagate(False)

        commit_hash = self.commit_data.get("hash", "")
        subject = self.commit_data.get("subject", "")
        author = self.commit_data.get("author", "")

        text = f"{commit_hash} | {subject} | {author}"

        label = ctk.CTkLabel(
            message_frame,
            text=text,
            text_color=APP_COLORS["text"],
            anchor="w",
            justify="left",
            font=ctk.CTkFont(size=13)
        )
        label.pack(fill="both", expand=True, padx=10)

    def _draw_graph(self, graph_prefix: str):
        canvas = self.canvas
        canvas.delete("all")

        if not graph_prefix:
            return

        step_x = 16
        left = 18
        mid_y = self.ROW_HEIGHT // 2
        top_y = -2
        bottom_y = self.ROW_HEIGHT + 2

        node_index = None
        for i, ch in enumerate(graph_prefix):
            if ch == "*":
                node_index = i
                break

        for i, ch in enumerate(graph_prefix):
            x = left + i * step_x
            color = GRAPH_COLORS[i % len(GRAPH_COLORS)]

            if ch == "|":
                canvas.create_line(x, top_y, x, bottom_y, fill=color, width=3)

            elif ch == "/":
                canvas.create_line(x + 8, bottom_y, x - 8, top_y, fill=color, width=3)

            elif ch == "\\":
                canvas.create_line(x - 8, bottom_y, x + 8, top_y, fill=color, width=3)

            elif ch == "_":
                canvas.create_line(x - 8, mid_y, x + 8, mid_y, fill=color, width=3)

            elif ch == "*":
                canvas.create_line(x, top_y, x, mid_y - 8, fill=color, width=3)
                canvas.create_line(x, mid_y + 8, x, bottom_y, fill=color, width=3)
                canvas.create_oval(
                    x - 8, mid_y - 8, x + 8, mid_y + 8,
                    fill=color,
                    outline=color
                )

        if node_index is not None and self.selected:
            node_x = left + node_index * step_x
            canvas.create_line(
                node_x + 8,
                mid_y,
                self.GRAPH_WIDTH - 6,
                mid_y,
                fill=GRAPH_COLORS[node_index % len(GRAPH_COLORS)],
                width=3
            )


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
        header.pack(fill="x", padx=0, pady=(0, 4))
        header.pack_propagate(False)

        header.grid_columnconfigure(0, weight=0, minsize=180)
        header.grid_columnconfigure(1, weight=0, minsize=150)
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

    def set_commit_rows(self, rows: list[dict]):
        self.clear()

        if not rows:
            self._empty_state("Nenhum commit encontrado.")
            return

        for index, row_data in enumerate(rows):
            branch_badge = self.current_branch if index == 0 and self.current_branch else ""

            row = CommitRow(
                self.scroll,
                branch_text=branch_badge,
                commit_data=row_data,
                selected=(index == 0),
                is_head=(index == 0)
            )
            row.pack(fill="x", padx=8, pady=0)

    def set_commits(self, commits: list[str]):
        self.clear()
        self._empty_state(commits[0] if commits else "Nenhum commit encontrado.")

    def _empty_state(self, text: str):
        container = ctk.CTkFrame(self.scroll, fg_color="transparent")
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