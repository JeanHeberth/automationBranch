import sys
import tkinter as tk
import tkinter.font as tkfont
import weakref

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


class HoverTooltip:
    """Tooltip ao passar o mouse.

    Usa uma única janela por aplicação, criada oculta e só mostrada/ocultada (withdraw), em vez
    de criar e destruir uma a cada passada do mouse. No macOS, em tela estendida (iPad), destruir
    janelas sem borda deixava um quadrado preto parado na tela."""

    _instances: "weakref.WeakSet[HoverTooltip]" = weakref.WeakSet()
    _shared: dict = {}  # root -> [janela, label, dono atual]

    def __init__(self, widget, text_getter):
        self.widget = widget
        self.text_getter = text_getter
        self.tip = None
        HoverTooltip._instances.add(self)

        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<Motion>", self.move, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def _shared_window(self):
        root = self.widget._root()
        entry = HoverTooltip._shared.get(root)
        if entry is None or not entry[0].winfo_exists():
            # tk.Toplevel/tk.Label puros: CTkToplevel + CTkLabel renderizam o tooltip vazio no
            # macOS (sem texto) e são lentos para criar/destruir no Windows.
            tip = tk.Toplevel(root)
            tip.withdraw()
            tip.wm_overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.configure(bg=APP_COLORS["border"])
            label = tk.Label(tip, fg=APP_COLORS["text"], bg="#111827", justify="left", padx=10, pady=6)
            label.pack(padx=1, pady=1)
            entry = [tip, label, None]
            HoverTooltip._shared[root] = entry
        return entry

    def show(self, event=None):
        text = self.text_getter()
        if not text:
            return

        if self.tip is not None:
            return

        # Com um popup modal aberto, o tooltip (topmost) apareceria por cima dele.
        try:
            grab = self.widget.grab_current()
        except Exception:
            grab = None
        if grab is not None and grab.winfo_toplevel() is not self.widget.winfo_toplevel():
            return

        entry = self._shared_window()
        entry[2] = self
        entry[1].configure(text=text)
        self.tip = entry[0]

        self.tip.update_idletasks()
        self.move(event)
        self.tip.deiconify()

    def move(self, event=None):
        if self.tip is None or event is None:
            return

        x = event.x_root + 12
        y = event.y_root + 12
        self.tip.geometry(f"+{x}+{y}")

    def hide(self, _event=None):
        if self.tip is None:
            return
        entry = HoverTooltip._shared.get(self.widget._root())
        # Só oculta se a janela compartilhada ainda é deste tooltip.
        if entry is not None and entry[2] is self and entry[0].winfo_exists():
            entry[0].withdraw()
            entry[2] = None
        self.tip = None

    @classmethod
    def hide_all(cls):
        """Fecha todos os tooltips visíveis (ex.: ao abrir um popup modal)."""
        for entry in list(cls._shared.values()):
            try:
                if entry[0].winfo_exists():
                    entry[0].withdraw()
                entry[2] = None
            except Exception:
                pass
        for instance in list(cls._instances):
            instance.tip = None


def _rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Retângulo de cantos arredondados como um único item do canvas (polígono suavizado)."""
    r = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def build_commit_tooltip_text(commit_data: dict) -> str:
    decorations = commit_data.get("decorations", "").strip()
    lines = []

    if decorations:
        clean = decorations
        if clean.startswith("(") and clean.endswith(")"):
            clean = clean[1:-1]
        clean = clean.replace("HEAD -> ", "")
        lines.append(f"Refs: {clean}")

    lines.append(f"Commit: {commit_data.get('hash', '')}")
    lines.append(f"Autor: {commit_data.get('author', '')}")
    lines.append(f"Mensagem: {commit_data.get('subject', '')}")

    if commit_data.get("is_merge", False):
        lines.append("Tipo: Merge commit")

    return "\n".join(lines)


class CenterPanel(ctk.CTkFrame):
    """Lista de commits (branch, grafo e mensagem).

    Tudo é desenhado num único tk.Canvas. Antes cada linha era um conjunto de ~10 widgets do
    CustomTkinter (frames arredondados, labels e um canvas por linha) e montar 25 linhas
    travava a janela por mais de 1 s no Windows; itens de canvas custam microssegundos.
    """

    ROW_HEIGHT = 34
    BRANCH_WIDTH = 170
    GRAPH_WIDTH = 150
    SELECTED_ROW_BG = "#16243a"
    SELECTED_MESSAGE_BG = "#0f2b57"

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0
        )

        self.current_branch = ""
        self._rows: list[dict] = []
        self._empty_text: str | None = None
        self._rendered_rows_key = None
        self._hover_index = None
        self._last_width = 0

        self._build_header()
        self._build_body()

    # ---------- montagem ----------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#2a2f3a", corner_radius=0, height=38)
        header.pack(fill="x", padx=0, pady=(0, 4))
        header.pack_propagate(False)

        header.grid_columnconfigure(0, weight=0, minsize=180)
        header.grid_columnconfigure(1, weight=0, minsize=150)
        header.grid_columnconfigure(2, weight=1)

        header_font = ctk.CTkFont(size=12, weight="bold")
        for column, text in enumerate(("BRANCH / TAG", "GRAPH", "COMMIT MESSAGE")):
            ctk.CTkLabel(
                header,
                text=text,
                text_color=APP_COLORS["muted"],
                font=header_font
            ).grid(row=0, column=column, sticky="w", padx=(14 if column == 0 else 8, 8), pady=8)

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        # Mesma escala (DPI) que o CustomTkinter aplica aos próprios widgets.
        try:
            self._scale = float(ctk.ScalingTracker.get_widget_scaling(self))
        except Exception:
            self._scale = 1.0

        family = ctk.CTkFont(size=13).cget("family")
        self._font_text = tkfont.Font(family=family, size=-self._px(13))
        self._font_badge = tkfont.Font(family=family, size=-self._px(12), weight="bold")

        self.canvas = tk.Canvas(
            body,
            bg=APP_COLORS["panel"],
            highlightthickness=0,
            bd=0,
            # Uma "unidade" de rolagem = uma linha de commit.
            yscrollincrement=self._px(self.ROW_HEIGHT),
        )
        self.scrollbar = ctk.CTkScrollbar(body, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._tooltip = HoverTooltip(self.canvas, self._hover_tooltip_text)
        self.canvas.bind("<Motion>", self._on_motion, add="+")
        self.canvas.bind("<Leave>", self._on_leave, add="+")

        # bind_all com add="+": não substitui a rolagem dos outros painéis (CTkScrollableFrame).
        if sys.platform.startswith("linux"):
            self.canvas.bind_all("<Button-4>", self._on_mouse_wheel, add="+")
            self.canvas.bind_all("<Button-5>", self._on_mouse_wheel, add="+")
        else:
            self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel, add="+")

    def _px(self, value: float) -> int:
        return int(round(value * self._scale))

    # ---------- API pública (mesma de antes) ----------
    def clear(self):
        self._rendered_rows_key = None
        self._rows = []
        self._empty_text = None
        self._hover_index = None
        self._tooltip.hide()
        self.canvas.delete("all")

    def set_current_branch(self, branch_name: str):
        self.current_branch = branch_name

    def set_commit_rows(self, rows: list[dict]):
        # Mesmos commits na mesma branch: não redesenha.
        key = (self.current_branch, rows)
        if rows and self._rendered_rows_key == key:
            return

        self.clear()
        if not rows:
            self._empty_state("Nenhum commit encontrado.")
            return

        self._rendered_rows_key = key
        self._rows = list(rows)
        self._redraw()
        self.canvas.yview_moveto(0)

    def set_commits(self, commits: list[str]):
        self.clear()
        self._empty_state(commits[0] if commits else "Nenhum commit encontrado.")

    def _empty_state(self, text: str):
        self._empty_text = text
        self._redraw()

    # ---------- desenho ----------
    def _on_canvas_configure(self, event):
        # Só a largura muda o desenho (fundo da mensagem e texto do estado vazio).
        if event.width != self._last_width:
            self._last_width = event.width
            self._redraw()

    def _redraw(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 1)

        if self._empty_text is not None:
            canvas.create_text(
                width / 2, self._px(70),
                text=self._empty_text,
                fill=APP_COLORS["muted"],
                font=self._font_text,
                width=max(width - self._px(40), 50),
                justify="center",
            )
            canvas.configure(scrollregion=(0, 0, width, self._px(140)))
            return

        row_h = self._px(self.ROW_HEIGHT)
        for index, row in enumerate(self._rows):
            self._draw_row(index, row, index * row_h, width)

        canvas.configure(scrollregion=(0, 0, width, len(self._rows) * row_h))

    def _columns(self) -> tuple[int, int, int]:
        """x inicial das colunas branch, grafo e mensagem (mesmos recuos das linhas antigas)."""
        px = self._px
        branch_left = px(8) + px(8)
        graph_left = branch_left + px(self.BRANCH_WIDTH) + px(6)
        message_left = graph_left + px(self.GRAPH_WIDTH) + px(6)
        return branch_left, graph_left, message_left

    def _draw_row(self, index: int, commit: dict, top: int, width: int):
        canvas = self.canvas
        px = self._px
        row_h = px(self.ROW_HEIGHT)
        selected = index == 0  # a primeira linha é o HEAD
        right = width - px(8)
        branch_left, graph_left, message_left = self._columns()

        if selected:
            canvas.create_rectangle(px(8), top, right, top + row_h, fill=self.SELECTED_ROW_BG, width=0)

        # Coluna 1: etiqueta da branch (só na linha do HEAD).
        if selected and self.current_branch:
            max_badge = px(self.BRANCH_WIDTH) - px(4) - px(36)  # reserva espaço para o "+2"
            next_x = self._draw_badge(
                branch_left, top, self.current_branch, "#108bb8", "#f8fafc", max_badge
            )
            self._draw_badge(next_x, top, "+2", "#2a2f3a", APP_COLORS["text"], px(40), pad=8)

        # Coluna 2: grafo.
        self._draw_graph(graph_left, top, commit.get("graph", ""), selected)

        # Coluna 3: mensagem.
        message_right = right - px(10)
        if selected and message_right > message_left:
            _rounded_rect(
                canvas, message_left, top, message_right, top + row_h, px(6),
                fill=self.SELECTED_MESSAGE_BG, outline="",
            )
        text = f"{commit.get('hash', '')} | {commit.get('subject', '')} | {commit.get('author', '')}"
        canvas.create_text(
            message_left + px(10), top + row_h / 2,
            text=text, anchor="w", fill=APP_COLORS["text"], font=self._font_text,
        )

    def _draw_badge(self, x, top, text, bg, fg, max_width, pad=10) -> int:
        """Desenha uma etiqueta arredondada e devolve o x onde a próxima pode começar."""
        px = self._px
        font = self._font_badge
        text = self._fit_text(text, font, max_width - 2 * px(pad))
        height = px(26)
        y1 = top + (px(self.ROW_HEIGHT) - height) / 2
        x2 = x + font.measure(text) + 2 * px(pad)
        _rounded_rect(self.canvas, x, y1, x2, y1 + height, px(6), fill=bg, outline="")
        self.canvas.create_text((x + x2) / 2, y1 + height / 2, text=text, fill=fg, font=font)
        return x2 + px(4)

    @staticmethod
    def _fit_text(text: str, font, max_width: int) -> str:
        if max_width <= 0 or font.measure(text) <= max_width:
            return text
        while text and font.measure(text + "…") > max_width:
            text = text[:-1]
        return text + "…"

    def _draw_graph(self, graph_left, top, graph_prefix: str, selected: bool):
        if not graph_prefix:
            return

        canvas = self.canvas
        px = self._px
        step_x = px(16)
        start = graph_left + px(18)
        half = px(8)
        line_w = max(1, px(3))
        row_h = px(self.ROW_HEIGHT)
        mid_y = top + row_h // 2
        top_y = top
        bottom_y = top + row_h

        for i, ch in enumerate(graph_prefix):
            x = start + i * step_x
            color = GRAPH_COLORS[i % len(GRAPH_COLORS)]

            if ch == "|":
                canvas.create_line(x, top_y, x, bottom_y, fill=color, width=line_w)
            elif ch == "/":
                canvas.create_line(x + half, bottom_y, x - half, top_y, fill=color, width=line_w)
            elif ch == "\\":
                canvas.create_line(x - half, bottom_y, x + half, top_y, fill=color, width=line_w)
            elif ch == "_":
                canvas.create_line(x - half, mid_y, x + half, mid_y, fill=color, width=line_w)
            elif ch == "*":
                canvas.create_line(x, top_y, x, mid_y - half, fill=color, width=line_w)
                canvas.create_line(x, mid_y + half, x, bottom_y, fill=color, width=line_w)
                canvas.create_oval(
                    x - half, mid_y - half, x + half, mid_y + half, fill=color, outline=color
                )

        node_index = graph_prefix.find("*")
        if node_index >= 0 and selected:
            node_x = start + node_index * step_x
            canvas.create_line(
                node_x + half, mid_y,
                graph_left + px(self.GRAPH_WIDTH) - px(6), mid_y,
                fill=GRAPH_COLORS[node_index % len(GRAPH_COLORS)],
                width=line_w,
            )

    # ---------- interação ----------
    def _row_under_pointer(self, event):
        """Índice da linha sob o mouse, só nas colunas de branch e grafo (como antes)."""
        if not self._rows or event is None:
            return None
        index = int(self.canvas.canvasy(event.y) // self._px(self.ROW_HEIGHT))
        if not 0 <= index < len(self._rows):
            return None
        _, graph_left, _ = self._columns()
        if event.x > graph_left + self._px(self.GRAPH_WIDTH):
            return None
        return index

    def _hover_tooltip_text(self):
        if self._hover_index is None or self._hover_index >= len(self._rows):
            return ""
        text = build_commit_tooltip_text(self._rows[self._hover_index])
        # A etiqueta pode estar truncada ("…"): mostra o nome completo da branch.
        if self._hover_index == 0 and self.current_branch:
            text = f"Branch: {self.current_branch}\n{text}"
        return text

    def _on_motion(self, event):
        index = self._row_under_pointer(event)
        if index == self._hover_index:
            return
        self._tooltip.hide()
        self._hover_index = index
        if index is not None:
            self._tooltip.show(event)

    def _on_leave(self, _event=None):
        self._hover_index = None

    def _on_mouse_wheel(self, event):
        try:
            if self.winfo_containing(event.x_root, event.y_root) is not self.canvas:
                return
        except Exception:
            return

        num = getattr(event, "num", None)
        if num == 4:
            units = -3
        elif num == 5:
            units = 3
        elif sys.platform == "darwin":
            units = -event.delta
        else:
            units = -int(event.delta / 120) * 3

        if units and self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(units, "units")
