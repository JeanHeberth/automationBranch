import threading
from tkinter import TclError

import customtkinter as ctk

from services.branch_service import get_local_and_remote_branches
from services.pull_request_service import (
    filter_pull_requests,
    get_pull_request,
    list_pull_requests,
    parse_pull_request_number,
)
from services.search_service import (
    MAX_CONTENT_RESULTS,
    MIN_CONTENT_QUERY,
    filter_branches,
    filter_paths,
    get_file_history,
    list_repo_files,
    search_commits,
    search_content,
)
from ui.theme import APP_COLORS, load_icon

TABS = ("Commits", "Arquivos", "Branches", "PRs", "Conteúdo")
PR_STATES = {"open": "aberto", "merged": "mergeado", "closed": "fechado"}
COMMIT_MODES = {"Mensagem": "message", "Autor": "author", "Código": "code"}
DEBOUNCE_MS = 250

# Dica mostrada na área de resultados enquanto nada foi digitado. Não usamos o placeholder do
# CTkEntry: ele é texto real dentro do campo e, se o evento de foco não chegar, o que o usuário
# digita fica depois dele e get() devolve "" (a busca nunca roda).
HINTS = {
    "Commits": {
        "Mensagem": "Busque commits pela mensagem ou pelo hash.",
        "Autor": "Busque commits pelo nome do autor.",
        "Código": "Descubra quem adicionou ou removeu um trecho de código.\nDigite o texto exato.",
    },
    "Arquivos": "Busque um arquivo pelo nome ou caminho.\nEscolha um para ver o histórico dele.",
    "Branches": "Busque uma branch local ou remota.\nEscolher faz o checkout.",
    "PRs": "Busque Pull Requests (abertos, mergeados e fechados)\npor número, título, branch ou autor.\nEscolher abre o PR no navegador.",
    "Conteúdo": "Busque um texto dentro dos arquivos do projeto.\nEscolher abre o arquivo na linha encontrada.",
}


class SearchDialog(ctk.CTkToplevel):
    """Busca global do repositório: commits (mensagem, autor, código), arquivos, branches,
    Pull Requests e conteúdo dos arquivos.

    Não é modal: dá para abrir vários diffs com a busca aberta. Os dados vêm do git em threads;
    `_token` descarta respostas de uma busca que já foi substituída por outra.
    """

    def __init__(
        self, master, repo_path: str, on_open_commit, on_checkout_branch, on_open_pr=None, on_open_file=None
    ):
        super().__init__(master)

        self.repo_path = repo_path
        self.on_open_commit = on_open_commit
        self.on_checkout_branch = on_checkout_branch
        self.on_open_pr = on_open_pr
        self.on_open_file = on_open_file

        self._tab = "Commits"
        self._commit_mode = "Mensagem"
        self._file_path: str | None = None  # arquivo cujo histórico está sendo mostrado
        self._token = 0
        self._debounce_job = None
        self._files_cache: list[str] | None = None
        self._branches_cache: tuple[list[str], list[str]] | None = None
        self._prs_cache: list[dict] | None = None
        self._first_action = None

        self.title("Buscar")
        self.geometry("620x560")
        self.minsize(480, 360)
        self.configure(fg_color=APP_COLORS["panel"])
        self.transient(master)

        self._build_ui()
        self._center(master)
        self._show_hint()

        self.bind("<Escape>", lambda _e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self.focus_entry)

    # ---------- construção ----------

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 8))

        ctk.CTkLabel(top, text="", image=load_icon("search.png", size=(18, 18))).pack(side="left", padx=(0, 8))

        self.entry = ctk.CTkEntry(
            top,
            height=38,
            corner_radius=8,
            fg_color="#2a2f3a",
            border_color=APP_COLORS["border"],
            text_color=APP_COLORS["text"],
            font=ctk.CTkFont(size=14),
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda _e: self._run_first_action())

        self.tabs = ctk.CTkSegmentedButton(
            self, values=list(TABS), command=self._on_tab_change, height=30
        )
        self.tabs.set(self._tab)
        self.tabs.pack(fill="x", padx=14, pady=(0, 6))

        self.mode_bar = ctk.CTkSegmentedButton(
            self, values=list(COMMIT_MODES), command=self._on_mode_change, height=26
        )
        self.mode_bar.set(self._commit_mode)
        self.mode_bar.pack(fill="x", padx=14, pady=(0, 6))

        self.results = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self.footer = ctk.CTkLabel(
            self, text="", anchor="w", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=11)
        )
        self.footer.pack(fill="x", padx=16, pady=(0, 10))

    def _center(self, master):
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + 80
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def focus_entry(self):
        if not self.winfo_exists():
            return
        self.lift()
        self.focus_force()
        self.entry.focus_set()

    def close(self):
        if self._debounce_job is not None:
            try:
                self.after_cancel(self._debounce_job)
            except (TclError, ValueError):
                pass
        self._token += 1  # respostas em andamento serão descartadas
        if self.winfo_exists():
            self.destroy()

    # ---------- eventos ----------

    def _on_tab_change(self, tab: str):
        self._tab = tab
        self._file_path = None
        if tab == "Commits":
            # after=tabs: o CTkScrollableFrame tem um frame interno, então não serve de âncora.
            self.mode_bar.pack(fill="x", padx=14, pady=(0, 6), after=self.tabs)
        else:
            self.mode_bar.pack_forget()
        self._search_now()
        self.entry.focus_set()

    def _on_mode_change(self, mode: str):
        self._commit_mode = mode
        self._search_now()
        self.entry.focus_set()

    def _on_key(self, event):
        if event.keysym in ("Return", "Escape", "Up", "Down", "Left", "Right", "Shift_L", "Shift_R"):
            return
        self._file_path = None  # digitar de novo sai do histórico de um arquivo
        if self._debounce_job is not None:
            self.after_cancel(self._debounce_job)
        self._debounce_job = self.after(DEBOUNCE_MS, self._search_now)

    def _run_first_action(self):
        if self._first_action:
            self._first_action()

    # ---------- busca ----------

    def _search_now(self):
        self._debounce_job = None
        query = self.entry.get().strip()
        self._token += 1
        token = self._token

        if self._file_path:
            path = self._file_path
            self._set_footer(f"Carregando histórico de {path}...")
            self._start(token, lambda: get_file_history(self.repo_path, path), self._render_commits, header=path)
            return

        if not query:
            self._show_hint()
            return

        self._set_footer("Buscando...")

        if self._tab == "Commits":
            mode = COMMIT_MODES[self._commit_mode]
            self._start(token, lambda: search_commits(self.repo_path, query, mode), self._render_commits)
        elif self._tab == "Arquivos":
            self._start(token, lambda: self._files_matching(query), self._render_files)
        elif self._tab == "Branches":
            self._start(token, lambda: self._branches_matching(query), self._render_branches)
        elif self._tab == "PRs":
            self._start(token, lambda: self._prs_matching(query), self._render_prs)
        else:
            if len(query) < MIN_CONTENT_QUERY:
                self._clear()
                self._set_footer(f"Digite ao menos {MIN_CONTENT_QUERY} caracteres.")
                return
            self._start(token, lambda: search_content(self.repo_path, query), self._render_content)

    def _files_matching(self, query: str) -> list[str]:
        if self._files_cache is None:
            self._files_cache = list_repo_files(self.repo_path)
        return filter_paths(self._files_cache, query)

    def _branches_matching(self, query: str) -> list[dict]:
        if self._branches_cache is None:
            self._branches_cache = get_local_and_remote_branches(self.repo_path)
        local, remote = self._branches_cache
        return filter_branches(local, remote, query)

    def _prs_matching(self, query: str) -> list[dict]:
        if self._prs_cache is None:
            self._prs_cache = list_pull_requests(self.repo_path)

        found = filter_pull_requests(self._prs_cache, query)

        # Um número antigo pode ter ficado fora dos PRs mais recentes: busca direto no GitHub.
        number = parse_pull_request_number(query)
        if not found and number is not None:
            pr = get_pull_request(self.repo_path, number)
            if pr:
                self._prs_cache.append(pr)
                found = [pr]

        return found

    def _start(self, token: int, work, render, header: str | None = None):
        def runner():
            try:
                data = work()
            except Exception as exc:
                self._deliver(token, lambda: self._show_error(str(exc)))
            else:
                self._deliver(token, lambda: render(data, header) if header else render(data))

        threading.Thread(target=runner, daemon=True).start()

    def _deliver(self, token: int, callback):
        def apply():
            # Descarta se outra busca começou ou a janela fechou.
            if self.winfo_exists() and token == self._token:
                callback()

        try:
            self.after(0, apply)
        except (RuntimeError, TclError):
            pass

    # ---------- resultados ----------

    def _clear(self):
        self._first_action = None
        for widget in self.results.winfo_children():
            widget.destroy()

    def _set_footer(self, text: str):
        self.footer.configure(text=text)

    def _show_hint(self):
        self._clear()

        hint = HINTS[self._tab]
        if isinstance(hint, dict):
            hint = hint[self._commit_mode]

        ctk.CTkLabel(
            self.results,
            text=hint,
            text_color=APP_COLORS["muted"],
            font=ctk.CTkFont(size=13),
            justify="center",
        ).pack(pady=40)
        self._set_footer("Digite para buscar. Enter abre o primeiro resultado, Esc fecha.")

    def _show_error(self, message: str):
        self._clear()
        self._set_footer(f"Erro: {message}")

    def _add_row(self, title: str, subtitle: str, command):
        row = ctk.CTkFrame(self.results, fg_color="#2a2f3a", corner_radius=8, cursor="hand2")
        row.pack(fill="x", padx=4, pady=2)

        title_label = ctk.CTkLabel(
            row, text=title, anchor="w", text_color=APP_COLORS["text"], font=ctk.CTkFont(size=12, weight="bold")
        )
        title_label.pack(fill="x", padx=10, pady=(6, 0))

        subtitle_label = ctk.CTkLabel(
            row, text=subtitle, anchor="w", text_color=APP_COLORS["muted"], font=ctk.CTkFont(size=11)
        )
        subtitle_label.pack(fill="x", padx=10, pady=(0, 6))

        def highlight(color):
            row.configure(fg_color=color)

        for widget in (row, title_label, subtitle_label):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", lambda _e: highlight(APP_COLORS["hover"]))
            widget.bind("<Leave>", lambda _e: highlight("#2a2f3a"))

        if self._first_action is None:
            self._first_action = command

    def _render_commits(self, rows: list[dict], header: str | None = None):
        self._clear()

        if header:
            self._add_row(f"Histórico de {header}", "Clique para voltar à busca", self._back_to_search)
            self._first_action = None  # o Enter abre o primeiro commit, não "voltar"

        for row in rows:
            self._add_row(
                f"{row['hash']}  {row['subject']}",
                f"{row['author']} · {row['date']}",
                lambda r=row: self.on_open_commit(r["hash"], r["subject"]),
            )

        self._set_footer(self._count_text(len(rows), "commit", "commits"))

    def _render_files(self, paths: list[str]):
        self._clear()

        for path in paths:
            name = path.rsplit("/", 1)[-1]
            folder = path[: -len(name)].rstrip("/") or "(raiz)"
            self._add_row(name, f"{folder} · clique para ver o histórico", lambda p=path: self._open_file(p))

        self._set_footer(self._count_text(len(paths), "arquivo", "arquivos"))

    def _render_branches(self, branches: list[dict]):
        self._clear()

        for branch in branches:
            kind = "remota (cria uma branch local ao trocar)" if branch["remote"] else "local"
            self._add_row(
                branch["name"],
                kind,
                lambda b=branch: self._checkout(b),
            )

        self._set_footer(self._count_text(len(branches), "branch", "branches"))

    def _render_prs(self, prs: list[dict]):
        self._clear()

        for pr in prs:
            state = PR_STATES.get(pr.get("state"), pr.get("state", ""))
            details = [f"{pr.get('head', '')} → {pr.get('base', '')}", state]
            if pr.get("author"):
                details.append(f"@{pr['author']}")
            self._add_row(f"#{pr['number']}  {pr['title']}", " · ".join(details), lambda p=pr: self._open_pr(p))

        self._set_footer(self._count_text(len(prs), "Pull Request", "Pull Requests"))

    def _render_content(self, rows: list[dict]):
        self._clear()

        for row in rows:
            self._add_row(
                f"{row['path']}:{row['line']}",
                row["text"] or "(linha em branco)",
                lambda r=row: self._open_content(r),
            )

        text = self._count_text(len(rows), "ocorrência", "ocorrências")
        if len(rows) >= MAX_CONTENT_RESULTS:
            text += f" (mostrando as primeiras {MAX_CONTENT_RESULTS}; refine a busca)"
        self._set_footer(text)

    @staticmethod
    def _count_text(count: int, singular: str, plural: str) -> str:
        if count == 0:
            return "Nenhum resultado."
        return f"{count} {singular if count == 1 else plural}"

    # ---------- ações ----------

    def _open_file(self, path: str):
        self._file_path = path
        self._search_now()

    def _back_to_search(self):
        self._file_path = None
        self._search_now()

    def _open_pr(self, pr: dict):
        if self.on_open_pr:
            self.on_open_pr(pr)

    def _open_content(self, row: dict):
        if self.on_open_file:
            self.on_open_file(row["path"], row["line"])

    def _checkout(self, branch: dict):
        name, is_remote = branch["name"], branch["remote"]
        self.close()
        self.on_checkout_branch(name, is_remote)
