import customtkinter as ctk

from ui.theme import APP_COLORS

_HIGHLIGHT_BG = "#3b3a1f"


class FileViewer(ctk.CTkToplevel):
    """Janela não modal que mostra um arquivo com números de linha e uma linha destacada."""

    def __init__(self, master, title: str, text: str, highlight_line: int | None = None):
        super().__init__(master)
        self.title(title)
        self.geometry("820x560")
        self.minsize(480, 320)
        self.transient(master)
        self.configure(fg_color=APP_COLORS["bg"])

        ctk.CTkLabel(
            self,
            text=title,
            anchor="w",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(fill="x", padx=14, pady=(12, 6))

        self._textbox = ctk.CTkTextbox(
            self,
            wrap="none",
            fg_color="#0b1220",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(family="Menlo", size=12),
        )
        self._textbox.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        inner = self._textbox._textbox  # tk.Text por baixo do CTkTextbox: permite tags
        inner.tag_config("target", background=_HIGHLIGHT_BG)
        inner.tag_config("gutter", foreground=APP_COLORS["muted"])

        self._render(text, highlight_line)
        self._textbox.configure(state="disabled")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(100, self.focus_force)

    def _render(self, text: str, highlight_line: int | None):
        inner = self._textbox._textbox
        lines = text.splitlines() or [""]
        width = len(str(len(lines)))

        for number, line in enumerate(lines, start=1):
            inner.insert("end", f"{number:>{width}}  ", "gutter")
            inner.insert("end", line + "\n")
            if number == highlight_line:
                inner.tag_add("target", f"{number}.0", f"{number}.0 lineend")

        if highlight_line:
            # Depois da janela ter tamanho: coloca a linha encontrada no meio da área visível.
            self.after(80, lambda: self._center_on(highlight_line))

    def _center_on(self, line: int):
        if not self.winfo_exists():
            return
        inner = self._textbox._textbox
        info = inner.dlineinfo("1.0")
        line_height = info[3] if info else 16
        visible_lines = max(inner.winfo_height() // line_height, 1)
        total_lines = int(inner.index("end-1c").split(".")[0])
        inner.yview_moveto(max(line - visible_lines // 2 - 1, 0) / total_lines)
