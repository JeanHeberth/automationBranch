import customtkinter as ctk
from ui.theme import APP_COLORS


class FileSection(ctk.CTkFrame):
    def __init__(self, master, title: str, kind: str, unchecked: set[str], on_toggle=None, on_action=None):
        super().__init__(master, fg_color="transparent")

        # kind: "staged" | "unstaged". on_action(action, kind, path, status) — "diff", "stage",
        # "unstage" ou "discard".
        self._kind = kind
        self._on_action = on_action

        # Conjunto compartilhado com o painel: caminhos desmarcados (o padrão é marcado).
        self._unchecked = unchecked
        self._on_toggle = on_toggle
        self._vars: dict[str, ctk.BooleanVar] = {}

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title_label.pack(anchor="w", padx=4, pady=(3, 5))

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="x", expand=False)

    @staticmethod
    def _split(file_text: str) -> tuple[str, str]:
        status, _, path = file_text.partition(" | ")
        return status, path

    def clear(self):
        self._vars = {}
        for widget in self.container.winfo_children():
            widget.destroy()

    def paths(self) -> list[str]:
        return list(self._vars)

    def sync_checks(self):
        for path, var in self._vars.items():
            var.set(path not in self._unchecked)

    def _toggle(self, path: str):
        if self._vars[path].get():
            self._unchecked.discard(path)
        else:
            self._unchecked.add(path)

        if self._on_toggle:
            self._on_toggle()

    def set_message(self, text: str):
        self.clear()
        label = ctk.CTkLabel(
            self.container,
            text=text,
            text_color=APP_COLORS["muted"],
            anchor="w",
            font=ctk.CTkFont(size=11)
        )
        label.pack(fill="x", padx=6, pady=(0, 6))

    def set_files(self, files: list[str]):
        self.clear()

        if not files:
            self.set_message("Nenhum arquivo")
            return

        for file_text in files:
            status, path = self._split(file_text)

            item = ctk.CTkFrame(
                self.container,
                fg_color="#2a2f3a",
                corner_radius=8,
                height=32
            )
            item.pack(fill="x", padx=4, pady=2)

            var = ctk.BooleanVar(value=path not in self._unchecked)
            self._vars[path] = var

            checkbox = ctk.CTkCheckBox(
                item,
                text="",
                width=24,
                variable=var,
                command=lambda p=path: self._toggle(p),
                checkbox_width=18,
                checkbox_height=18,
            )
            checkbox.pack(side="left", padx=(8, 0), pady=6)

            if self._kind == "staged":
                self._add_button(item, "−", "unstage", path, status)
            else:
                self._add_button(item, "✕", "discard", path, status, danger=True)
                self._add_button(item, "+", "stage", path, status)

            label = ctk.CTkLabel(
                item,
                text=f"{status} | {path}",
                text_color=APP_COLORS["text"],
                anchor="w",
                cursor="hand2",
                font=ctk.CTkFont(size=11)
            )
            label.pack(side="left", fill="x", expand=True, padx=(2, 4), pady=6)
            label.bind("<Button-1>", lambda _e, p=path, st=status: self._emit("diff", p, st))

    def _emit(self, action: str, path: str, status: str):
        if self._on_action:
            self._on_action(action, self._kind, path, status)

    def _add_button(self, parent, text, action, path, status, danger=False):
        button = ctk.CTkButton(
            parent,
            text=text,
            width=24,
            height=22,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#7f1d1d" if danger else APP_COLORS["hover"],
            text_color=APP_COLORS["danger"] if danger else APP_COLORS["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._emit(action, path, status),
        )
        button.pack(side="right", padx=(0, 4), pady=4)


class StashSection(ctk.CTkFrame):
    """Lista de stashes; cada item abre o diff ao clicar e tem Aplicar / Pop / Descartar."""

    def __init__(self, master, on_action=None):
        super().__init__(master, fg_color="transparent")
        self._on_action = on_action

        self.title_label = ctk.CTkLabel(
            self,
            text="Stashes",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.title_label.pack(anchor="w", padx=4, pady=(3, 5))

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="x", expand=False)

    def clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def set_message(self, text: str):
        self.clear()
        ctk.CTkLabel(
            self.container,
            text=text,
            text_color=APP_COLORS["muted"],
            anchor="w",
            font=ctk.CTkFont(size=11)
        ).pack(fill="x", padx=6, pady=(0, 6))

    def set_stashes(self, stashes: list[dict]):
        self.clear()

        if not stashes:
            self.set_message("Nenhum stash")
            return

        for stash in stashes:
            ref = stash["ref"]
            item = ctk.CTkFrame(self.container, fg_color="#2a2f3a", corner_radius=8)
            item.pack(fill="x", padx=4, pady=2)

            origin = " · ".join(part for part in (stash.get("branch"), stash.get("date")) if part)
            label = ctk.CTkLabel(
                item,
                text=f"{ref}  {stash['message']}\n{origin}" if origin else f"{ref}  {stash['message']}",
                text_color=APP_COLORS["text"],
                anchor="w",
                justify="left",
                wraplength=200,
                cursor="hand2",
                font=ctk.CTkFont(size=11)
            )
            label.pack(fill="x", padx=8, pady=(6, 2))
            label.bind("<Button-1>", lambda _e, r=ref: self._emit("diff", r))

            buttons = ctk.CTkFrame(item, fg_color="transparent")
            buttons.pack(fill="x", padx=6, pady=(0, 6))
            self._add_button(buttons, "Aplicar", "apply", ref)
            self._add_button(buttons, "Pop", "pop", ref)
            self._add_button(buttons, "Descartar", "drop", ref, danger=True)

    def _emit(self, action: str, ref: str):
        if self._on_action:
            self._on_action(action, ref)

    def _add_button(self, parent, text, action, ref, danger=False):
        ctk.CTkButton(
            parent,
            text=text,
            width=58,
            height=22,
            corner_radius=6,
            fg_color="#334155" if not danger else "transparent",
            hover_color="#475569" if not danger else "#7f1d1d",
            text_color=APP_COLORS["danger"] if danger else "#ffffff",
            font=ctk.CTkFont(size=11),
            command=lambda: self._emit(action, ref),
        ).pack(side="left", padx=(0, 4))


class RightPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=APP_COLORS["panel"],
            corner_radius=0
        )

        self.commit_placeholder = "Digite a mensagem do commit..."
        self.is_placeholder_active = True
        self._unchecked: set[str] = set()
        self._on_file_action = None
        self._on_stash_action = None

        self._build_header()
        self._build_file_list()
        self._build_commit_area()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent", height=42)
        header.pack(fill="x", padx=8, pady=(6, 3))

        self.title = ctk.CTkLabel(
            header,
            text="Changes / Commit",
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.title.pack(side="left")

    def _build_file_list(self):
        self.files_container = ctk.CTkFrame(self, fg_color="transparent")
        self.files_container.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.scroll = ctk.CTkScrollableFrame(
            self.files_container,
            fg_color="transparent",
            height=240
        )
        self.scroll.pack(fill="both", expand=True)

        self.select_all_var = ctk.BooleanVar(value=True)
        self.select_all_check = ctk.CTkCheckBox(
            self.scroll,
            text="Selecionar todos",
            variable=self.select_all_var,
            command=self._toggle_all,
            text_color=APP_COLORS["muted"],
            checkbox_width=18,
            checkbox_height=18,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.select_all_check.pack(anchor="w", padx=8, pady=(0, 4))

        self.staged_section = FileSection(
            self.scroll, "Staged Files", "staged", self._unchecked, self._refresh_checks, self._handle_file_action
        )
        self.staged_section.pack(fill="x", pady=(0, 8))

        self.unstaged_section = FileSection(
            self.scroll, "Unstaged Files", "unstaged", self._unchecked, self._refresh_checks, self._handle_file_action
        )
        self.unstaged_section.pack(fill="x", pady=(0, 8))

        self.stash_section = StashSection(self.scroll, self._handle_stash_action)
        self.stash_section.pack(fill="x", pady=(0, 8))

    def _build_commit_area(self):
        divider = ctk.CTkFrame(self, fg_color=APP_COLORS["border"], height=1)
        divider.pack(fill="x", padx=8, pady=(3, 6))

        commit_container = ctk.CTkFrame(self, fg_color="transparent")
        commit_container.pack(fill="x", padx=8, pady=(0, 8))

        commit_title = ctk.CTkLabel(
            commit_container,
            text="Mensagem de commit",
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        commit_title.pack(anchor="w", pady=(0, 5))

        self.commit_msg = ctk.CTkTextbox(
            commit_container,
            height=92,
            corner_radius=8,
            fg_color="#2a2f3a",
            text_color=APP_COLORS["muted"],
            border_width=1,
            border_color=APP_COLORS["border"]
        )
        self.commit_msg.pack(fill="x", pady=(0, 8))
        self.commit_msg.insert("1.0", self.commit_placeholder)

        self.commit_msg.bind("<FocusIn>", self._handle_commit_focus_in)
        self.commit_msg.bind("<FocusOut>", self._handle_commit_focus_out)

        buttons_row = ctk.CTkFrame(commit_container, fg_color="transparent")
        buttons_row.pack(fill="x")
        buttons_row.grid_columnconfigure(0, weight=3)
        buttons_row.grid_columnconfigure(1, weight=1)

        self.commit_btn = ctk.CTkButton(
            buttons_row,
            text="Commit",
            height=36,
            fg_color=APP_COLORS["accent"],
            hover_color="#2563eb",
            text_color="#ffffff",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.commit_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.amend_btn = ctk.CTkButton(
            buttons_row,
            text="Amend",
            height=36,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#ffffff",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.amend_btn.grid(row=0, column=1, sticky="ew")

        self.stash_btn = ctk.CTkButton(
            buttons_row,
            text="Stash",
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            text_color="#ffffff",
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.stash_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    def _handle_commit_focus_in(self, _event=None):
        if self.is_placeholder_active:
            self.commit_msg.delete("1.0", "end")
            self.commit_msg.configure(text_color=APP_COLORS["text"])
            self.is_placeholder_active = False

    def _handle_commit_focus_out(self, _event=None):
        content = self.commit_msg.get("1.0", "end").strip()

        if not content:
            self._restore_placeholder()

    def _restore_placeholder(self):
        self.commit_msg.delete("1.0", "end")
        self.commit_msg.insert("1.0", self.commit_placeholder)
        self.commit_msg.configure(text_color=APP_COLORS["muted"])
        self.is_placeholder_active = True

    def _handle_file_action(self, action: str, kind: str, path: str, status: str):
        if self._on_file_action:
            self._on_file_action(action, kind, path, status)

    def set_on_file_action(self, callback):
        """callback(action, kind, path, status): action ∈ diff | stage | unstage | discard."""
        self._on_file_action = callback

    def _handle_stash_action(self, action: str, ref: str):
        if self._on_stash_action:
            self._on_stash_action(action, ref)

    def set_on_stash_action(self, callback):
        """callback(action, ref): action ∈ diff | apply | pop | drop."""
        self._on_stash_action = callback

    def set_on_stash(self, callback):
        self.stash_btn.configure(command=callback)

    def set_stashes(self, stashes: list[dict]):
        self.stash_section.set_stashes(stashes)

    def set_stashes_error(self, message: str):
        self.stash_section.set_message(f"Erro: {message}")

    def _all_paths(self) -> set[str]:
        return set(self.staged_section.paths()) | set(self.unstaged_section.paths())

    def _refresh_checks(self):
        """Mantém sincronizado o mesmo arquivo nas duas seções e o "Selecionar todos"."""
        self.staged_section.sync_checks()
        self.unstaged_section.sync_checks()
        all_paths = self._all_paths()
        self.select_all_var.set(bool(all_paths) and not (all_paths & self._unchecked))

    def _toggle_all(self):
        if self.select_all_var.get():
            self._unchecked.clear()
        else:
            self._unchecked.update(self._all_paths())
        self._refresh_checks()

    def get_selected_files(self) -> list[str]:
        return sorted(self._all_paths() - self._unchecked)

    def set_files_grouped(self, staged_files: list[str], unstaged_files: list[str]):
        self.staged_section.set_files(staged_files)
        self.unstaged_section.set_files(unstaged_files)
        # Esquece desmarcações de arquivos que não estão mais alterados (ex.: já commitados).
        self._unchecked &= self._all_paths()
        self._refresh_checks()

    def set_files_error(self, message: str):
        self.staged_section.set_message(f"Erro: {message}")
        self.unstaged_section.set_files([])
        self._unchecked.clear()
        self._refresh_checks()

    def set_files(self, files: list[str]):
        self.set_files_grouped(files, [])

    def get_commit_message(self) -> str:
        if self.is_placeholder_active:
            return ""
        return self.commit_msg.get("1.0", "end").strip()

    def clear_commit_message(self):
        self._restore_placeholder()

    def set_commit_message(self, text: str):
        self.commit_msg.delete("1.0", "end")
        self.commit_msg.insert("1.0", text)
        self.commit_msg.configure(text_color=APP_COLORS["text"])
        self.is_placeholder_active = False

    def set_on_commit(self, callback):
        self.commit_btn.configure(command=callback)

    def set_on_amend(self, callback):
        self.amend_btn.configure(command=callback)