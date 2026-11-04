import customtkinter as ctk

from ui.theme import APP_COLORS

_ADDED = "#4ade80"
_REMOVED = "#f87171"
_HUNK = "#60a5fa"


class DiffViewer(ctk.CTkToplevel):
    """Janela não modal que mostra o diff de um arquivo, com + e - coloridos."""

    def __init__(self, master, title: str, diff_text: str):
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

        inner = self._textbox._textbox  # tk.Text por baixo do CTkTextbox: permite tags de cor.
        inner.tag_config("added", foreground=_ADDED)
        inner.tag_config("removed", foreground=_REMOVED)
        inner.tag_config("hunk", foreground=_HUNK)
        inner.tag_config("meta", foreground=APP_COLORS["muted"])

        self._render(diff_text)
        self._textbox.configure(state="disabled")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(100, self.focus_force)

    @staticmethod
    def _tag_for(line: str) -> str | None:
        if line.startswith(("+++", "---", "diff ", "index ")):
            return "meta"
        if line.startswith("@@"):
            return "hunk"
        if line.startswith("+"):
            return "added"
        if line.startswith("-"):
            return "removed"
        return None

    def _render(self, diff_text: str):
        inner = self._textbox._textbox
        for line in diff_text.splitlines():
            tag = self._tag_for(line)
            inner.insert("end", line + "\n", tag or ())
