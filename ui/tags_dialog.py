import customtkinter as ctk

from ui.window_position import center_on_master

from ui.theme import APP_COLORS


class TagsDialog(ctk.CTkToplevel):
    """Lista de tags com Enviar, Apagar (local) e Apagar no remoto."""

    def __init__(self, master, tags: list[dict], on_action, on_new):
        super().__init__(master)
        self.withdraw()  # exibida só depois de posicionada (ver center_on_master)

        self.on_action = on_action  # on_action(action, name): "push" | "delete" | "delete_remote"
        self.on_new = on_new

        self.title("Tags")
        self.geometry("640x520")
        self.minsize(500, 340)
        self.configure(fg_color=APP_COLORS["panel"])
        self.transient(master)

        self._build_ui()
        self.set_tags(tags)
        self._center(master)
        self.bind("<Escape>", lambda _e: self.close())
        self.after(150, self._take_focus)

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header, text="Tags", text_color=APP_COLORS["text"], font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Nova tag…", width=110, height=32, corner_radius=8,
            fg_color=APP_COLORS["accent"], hover_color="#2563eb", text_color="#ffffff",
            font=ctk.CTkFont(size=12, weight="bold"), command=self.on_new,
        ).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 12))

    def set_tags(self, tags: list[dict]):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not tags:
            ctk.CTkLabel(self.list_frame, text="Nenhuma tag.", text_color=APP_COLORS["muted"]).pack(pady=30)
            return

        for tag in tags:
            self._add_row(tag)

    def _add_row(self, tag: dict):
        name = tag["name"]
        row = ctk.CTkFrame(self.list_frame, fg_color="#2a2f3a", corner_radius=8)
        row.pack(fill="x", padx=4, pady=2)

        kind = "anotada" if tag["annotated"] else "leve"
        detail = " · ".join(part for part in (tag["date"], kind, tag["subject"]) if part)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=10, pady=6)

        ctk.CTkLabel(
            info, text=name, anchor="w", text_color=APP_COLORS["text"], font=ctk.CTkFont(size=13, weight="bold")
        ).pack(fill="x")
        ctk.CTkLabel(
            info, text=detail, anchor="w", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=11)
        ).pack(fill="x")

        for text, action, danger in (
            ("Apagar remota", "delete_remote", True),
            ("Apagar", "delete", True),
            ("Enviar", "push", False),
        ):
            ctk.CTkButton(
                row, text=text, width=96 if "remota" in text else 64, height=26, corner_radius=6,
                fg_color="transparent" if danger else "#334155",
                hover_color="#7f1d1d" if danger else "#475569",
                text_color=APP_COLORS["danger"] if danger else "#ffffff",
                font=ctk.CTkFont(size=11),
                command=lambda a=action, n=name: self.on_action(a, n),
            ).pack(side="right", padx=(0, 6), pady=8)

    def _center(self, master):
        center_on_master(self, master, top_offset=60)

    def _take_focus(self):
        if self.winfo_exists():
            self.lift()
            self.focus_force()

    def close(self):
        if self.winfo_exists():
            self.destroy()
