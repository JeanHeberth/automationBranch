import os
import webbrowser
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog

from ui.top_bar import TopBar
from ui.left_sidebar import LeftSidebar
from ui.center_panel import CenterPanel
from ui.right_panel import RightPanel
from ui.profile_popup import ProfileConnectPopup
from ui.profile_menu import ProfileMenu
from ui.theme import APP_COLORS

from services.git_runner import GitServiceError
from services.branch_service import (
    is_git_repository,
    get_local_branches,
    get_remote_branches,
    get_remotes,
    get_current_branch,
    checkout_branch,
    create_branch,
)
from services.commit_service import (
    get_recent_commit_rows,
    get_changed_files_grouped,
    stage_all_changes,
    commit_all_changes,
)
from services.pull_request_service import (
    list_open_pull_requests,
    create_pull_request,
    merge_pull_request,
    find_open_pull_request_by_head,
)
from services.sync_service import (
    git_pull,
    git_push,
    git_stash,
    git_stash_pop,
)
from services.auth_service import (
    get_current_session,
    login_with_provider,
    logout,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Automation Branch")
        self.configure(fg_color=APP_COLORS["bg"])

        self.selected_repo_path: str | None = None
        self.repositories: dict[str, str] = {}
        self.is_updating_branch_ui = False
        self.profile_menu_popup = None

        self._configure_window_size()
        self._configure_grid()

        self.top_bar = TopBar(
            self,
            on_select_repo=self.handle_select_repository,
            on_action=self.handle_top_action,
            on_branch_change=self.handle_top_branch_changed
        )
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="nsew")

        self.left_sidebar = LeftSidebar(
            self,
            on_branch_select=self.handle_branch_selected,
            on_open_pr=self.handle_open_pr_item,
            on_merge_pr=self.handle_merge_pr_item
        )
        self.left_sidebar.grid(row=1, column=0, sticky="nsew")
        self.left_sidebar.grid_propagate(False)

        self.center_panel = CenterPanel(self)
        self.center_panel.grid(row=1, column=1, sticky="nsew")

        self.right_panel = RightPanel(self)
        self.right_panel.grid(row=1, column=2, sticky="nsew")
        self.right_panel.set_on_commit(self.handle_commit)

        self.status_label = ctk.CTkLabel(
            self,
            text="Selecione um repositório para começar.",
            anchor="w",
            fg_color=APP_COLORS["topbar"],
            text_color=APP_COLORS["text"],
            corner_radius=0,
            height=32
        )
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="ew")

        self._load_initial_data()
        self._refresh_profile_ui()

    def _configure_window_size(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = int(screen_width * 0.92)
        height = int(screen_height * 0.88)

        min_width = 1100
        min_height = 680

        width = max(width, min_width)
        height = max(height, min_height)

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min_width, min_height)

    def _configure_grid(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=340)

    def _load_initial_data(self):
        self.top_bar.set_branches([], current_branch="")
        self.left_sidebar.set_branches([], remote_branches=[], remotes=[])
        self.left_sidebar.set_pull_requests([])
        self.center_panel.set_current_branch("")
        self.center_panel.set_commit_rows([])
        self.right_panel.set_files_grouped([], [])

    def _refresh_profile_ui(self):
        session = get_current_session()

        if session.get("is_authenticated"):
            label = session.get("provider", "Conta")
        else:
            label = "Profile"

        self.top_bar.set_profile_label(label)

    def _open_profile_connect_popup(self):
        ProfileConnectPopup(
            self,
            on_github=self._connect_github,
            on_google=self._connect_google
        )

    def _open_profile_menu(self):
        if self.profile_menu_popup is not None and self.profile_menu_popup.winfo_exists():
            self.profile_menu_popup.destroy()

        self.profile_menu_popup = ProfileMenu(
            self,
            anchor_widget=self.top_bar.profile_btn,
            session_data=get_current_session(),
            on_connect=self._open_profile_connect_popup,
            on_logout=self._logout_profile
        )

    def _connect_github(self):
        session = login_with_provider("github")
        self._refresh_profile_ui()
        self.set_status(f"Conta conectada com sucesso via {session['provider']}.")

    def _connect_google(self):
        session = login_with_provider("google")
        self._refresh_profile_ui()
        self.set_status(f"Conta conectada com sucesso via {session['provider']}.")

    def _logout_profile(self):
        logout()
        self._refresh_profile_ui()
        self.set_status("Conta desconectada com sucesso.")

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def load_commits_for_branch(self, branch_name: str):
        if not self.selected_repo_path:
            self.center_panel.set_current_branch("")
            self.center_panel.set_commit_rows([])
            return

        try:
            rows = get_recent_commit_rows(self.selected_repo_path, branch_name, limit=25)
            self.center_panel.set_current_branch(branch_name)

            if not rows:
                self.center_panel.set_commit_rows([])
            else:
                self.center_panel.set_commit_rows(rows)

        except GitServiceError as exc:
            self.center_panel.set_current_branch(branch_name)
            self.center_panel.set_commits([
                "Erro ao carregar commits.",
                str(exc)
            ])

    def load_changed_files(self):
        if not self.selected_repo_path:
            self.right_panel.set_files_grouped([], [])
            return

        try:
            grouped = get_changed_files_grouped(self.selected_repo_path)
            self.right_panel.set_files_grouped(
                grouped.get("staged", []),
                grouped.get("unstaged", [])
            )

        except GitServiceError as exc:
            self.right_panel.set_files_grouped(
                [f"Erro: {str(exc)}"],
                []
            )

    def load_pull_requests(self):
        if not self.selected_repo_path:
            self.left_sidebar.set_pull_requests([])
            return

        try:
            prs = list_open_pull_requests(self.selected_repo_path)
            self.left_sidebar.set_pull_requests(prs)
        except GitServiceError:
            self.left_sidebar.set_pull_requests([])

    def sync_branch_ui(self, branch_name: str):
        if not self.selected_repo_path:
            return

        branches = get_local_branches(self.selected_repo_path)
        remote_branches = get_remote_branches(self.selected_repo_path)
        remotes = get_remotes(self.selected_repo_path)

        self.is_updating_branch_ui = True
        try:
            self.top_bar.set_branches(branches, current_branch=branch_name)
            self.top_bar.set_selected_branch(branch_name)

            self.left_sidebar.set_branches(
                branches,
                remote_branches=remote_branches,
                remotes=remotes
            )
            self.left_sidebar.set_selected_branch(branch_name)
            self.left_sidebar.set_footer_message(f"Branch atual: {branch_name}")
            self.left_sidebar.set_viewing_count(len(branches))
        finally:
            self.is_updating_branch_ui = False

        self.load_commits_for_branch(branch_name)
        self.load_changed_files()
        self.load_pull_requests()

    def perform_branch_checkout(self, branch_name: str):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de trocar de branch."
            )
            return

        try:
            checkout_branch(self.selected_repo_path, branch_name)
            current_branch = get_current_branch(self.selected_repo_path)

            self.sync_branch_ui(current_branch)
            self.set_status(f"Checkout realizado com sucesso para: {current_branch}")

        except GitServiceError as exc:
            messagebox.showerror("Erro no checkout", str(exc))
            self.set_status(f"Falha ao trocar para a branch: {branch_name}")

    def handle_commit(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de fazer commit."
            )
            return

        commit_message = self.right_panel.get_commit_message()

        if not commit_message:
            messagebox.showwarning(
                "Mensagem obrigatória",
                "Digite a mensagem do commit antes de continuar."
            )
            return

        try:
            stage_all_changes(self.selected_repo_path)
            result = commit_all_changes(self.selected_repo_path, commit_message)

            current_branch = get_current_branch(self.selected_repo_path)
            self.sync_branch_ui(current_branch)
            self.right_panel.clear_commit_message()

            self.set_status("Commit realizado com sucesso.")
            messagebox.showinfo("Commit", result or "Commit realizado com sucesso.")

        except GitServiceError as exc:
            messagebox.showerror("Erro no commit", str(exc))
            self.set_status("Falha ao executar commit.")

    def _handle_open_pr(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de abrir Pull Request."
            )
            return

        current_branch = get_current_branch(self.selected_repo_path)

        if current_branch == "main":
            messagebox.showwarning(
                "Branch inválida",
                "Não faz sentido abrir PR da branch main para ela mesma."
            )
            return

        existing_pr = find_open_pull_request_by_head(self.selected_repo_path, current_branch)
        if existing_pr:
            self.load_pull_requests()
            self.set_status(f"PR já existe para a branch {current_branch}.")
            messagebox.showinfo(
                "Pull Request existente",
                f"PR #{existing_pr['number']} já está aberto.\n\n{existing_pr['title']}\n{existing_pr['url']}"
            )
            return

        title = simpledialog.askstring(
            "Abrir Pull Request",
            "Título do PR:",
            initialvalue=f"{current_branch} -> main"
        )
        if not title:
            return

        body = simpledialog.askstring(
            "Descrição do PR",
            "Descrição do PR (opcional):",
            initialvalue=""
        )
        if body is None:
            body = ""

        try:
            pr = create_pull_request(
                self.selected_repo_path,
                title=title,
                body=body,
                base_branch="main",
                head_branch=current_branch
            )

            self.load_pull_requests()
            self.set_status(f"PR aberto com sucesso: #{pr['number']}")
            messagebox.showinfo(
                "Pull Request criado",
                f"PR #{pr['number']} criado com sucesso.\n\n{pr['title']}\n{pr['url']}"
            )

        except GitServiceError as exc:
            messagebox.showerror("Erro ao abrir PR", str(exc))
            self.set_status("Falha ao abrir Pull Request.")

    def _handle_merge_pr(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de mergear Pull Request."
            )
            return

        current_branch = get_current_branch(self.selected_repo_path)
        current_pr = find_open_pull_request_by_head(self.selected_repo_path, current_branch)

        pr_number = None
        pr_title = ""

        if current_pr:
            pr_number = current_pr["number"]
            pr_title = current_pr["title"]
        else:
            prs = list_open_pull_requests(self.selected_repo_path)

            if not prs:
                messagebox.showwarning(
                    "Sem Pull Requests",
                    "Não há Pull Requests abertos para mergear."
                )
                return

            if len(prs) == 1:
                pr_number = prs[0]["number"]
                pr_title = prs[0]["title"]
            else:
                selected = simpledialog.askstring(
                    "Merge Pull Request",
                    "Digite o número do PR que deseja mergear:"
                )
                if not selected:
                    return

                try:
                    pr_number = int(selected)
                except ValueError:
                    messagebox.showwarning("Valor inválido", "Digite um número de PR válido.")
                    return

                for pr in prs:
                    if pr["number"] == pr_number:
                        pr_title = pr["title"]
                        break

        confirm = messagebox.askyesno(
            "Confirmar merge",
            f"Deseja mergear o PR #{pr_number}?\n\n{pr_title}"
        )
        if not confirm:
            return

        try:
            result = merge_pull_request(self.selected_repo_path, pr_number)

            self.load_pull_requests()
            current_branch = get_current_branch(self.selected_repo_path)
            self.sync_branch_ui(current_branch)

            self.set_status(f"PR #{pr_number} mergeado com sucesso.")
            messagebox.showinfo(
                "Merge realizado",
                result.get("message", f"PR #{pr_number} mergeado com sucesso.")
            )

        except GitServiceError as exc:
            messagebox.showerror("Erro ao mergear PR", str(exc))
            self.set_status("Falha ao mergear Pull Request.")

    def handle_open_pr_item(self, pr: dict):
        url = pr.get("url", "").strip()
        if not url:
            messagebox.showwarning("PR sem URL", "Esse Pull Request não possui URL para abrir.")
            return

        try:
            webbrowser.open(url)
            self.set_status(f"Abrindo PR #{pr.get('number')} no navegador.")
        except Exception as exc:
            messagebox.showerror("Erro ao abrir PR", str(exc))

    def handle_merge_pr_item(self, pr: dict):
        pr_number = pr.get("number")
        pr_title = pr.get("title", "")

        if not pr_number:
            messagebox.showwarning("PR inválido", "Não foi possível identificar o número do PR.")
            return

        confirm = messagebox.askyesno(
            "Confirmar merge",
            f"Deseja mergear o PR #{pr_number}?\n\n{pr_title}"
        )
        if not confirm:
            return

        try:
            result = merge_pull_request(self.selected_repo_path, int(pr_number))

            self.load_pull_requests()
            current_branch = get_current_branch(self.selected_repo_path)
            self.sync_branch_ui(current_branch)

            self.set_status(f"PR #{pr_number} mergeado com sucesso.")
            messagebox.showinfo(
                "Merge realizado",
                result.get("message", f"PR #{pr_number} mergeado com sucesso.")
            )

        except GitServiceError as exc:
            messagebox.showerror("Erro ao mergear PR", str(exc))
            self.set_status("Falha ao mergear Pull Request.")

    def handle_top_action(self, action_name: str):
        self.set_status(f"Ação executada: {action_name}")

        if action_name == "Terminal":
            messagebox.showinfo("Terminal", "Depois podemos conectar isso ao terminal real.")
            return

        if action_name == "Open PR":
            self._handle_open_pr()
            return

        if action_name == "Merge PR":
            self._handle_merge_pr()
            return

        if action_name == "Profile":
            self._open_profile_menu()
            return

        if not self.selected_repo_path and action_name in {"Pull", "Push", "Branch", "Stash", "Pop", "Refresh"}:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de executar ações Git."
            )
            return

        try:
            if action_name == "Pull":
                result = git_pull(self.selected_repo_path)
                current_branch = get_current_branch(self.selected_repo_path)
                self.sync_branch_ui(current_branch)
                self.set_status("Pull executado com sucesso.")
                messagebox.showinfo("Pull", result or "Pull executado com sucesso.")

            elif action_name == "Push":
                result = git_push(self.selected_repo_path)
                current_branch = get_current_branch(self.selected_repo_path)
                self.sync_branch_ui(current_branch)
                self.set_status("Push executado com sucesso.")
                messagebox.showinfo(
                    "Push",
                    result or f"Push executado com sucesso para a branch {current_branch}."
                )

            elif action_name == "Branch":
                branch_name = simpledialog.askstring("Criar branch", "Digite o nome da nova branch:")
                if not branch_name:
                    return

                result = create_branch(self.selected_repo_path, branch_name.strip())
                current_branch = get_current_branch(self.selected_repo_path)
                self.sync_branch_ui(current_branch)

                self.set_status(f"Branch criada com sucesso: {current_branch}")
                messagebox.showinfo("Nova branch", result or f"Branch '{current_branch}' criada com sucesso.")

            elif action_name == "Stash":
                result = git_stash(self.selected_repo_path)
                self.sync_branch_ui(get_current_branch(self.selected_repo_path))
                self.set_status("Stash executado com sucesso.")
                messagebox.showinfo("Stash", result or "Stash executado com sucesso.")

            elif action_name == "Pop":
                result = git_stash_pop(self.selected_repo_path)
                self.sync_branch_ui(get_current_branch(self.selected_repo_path))
                self.set_status("Stash pop executado com sucesso.")
                messagebox.showinfo("Pop", result or "Stash pop executado com sucesso.")

            elif action_name == "Refresh":
                current_branch = get_current_branch(self.selected_repo_path)
                self.sync_branch_ui(current_branch)
                self.set_status("Dados atualizados com sucesso.")
                messagebox.showinfo("Refresh", "Dados atualizados com sucesso.")

            elif action_name == "Undo":
                messagebox.showinfo("Undo", "Função de desfazer ainda será implementada.")
            elif action_name == "Redo":
                messagebox.showinfo("Redo", "Função de refazer ainda será implementada.")
            elif action_name == "Actions":
                messagebox.showinfo("Actions", "Menu de ações extras ainda será implementado.")
            elif action_name == "Search":
                messagebox.showinfo("Search", "Busca ainda será implementada.")

        except GitServiceError as exc:
            messagebox.showerror("Erro Git", str(exc))
            self.set_status(f"Erro ao executar ação: {action_name}")

    def handle_select_repository(self):
        folder = filedialog.askdirectory(title="Selecionar repositório")

        if not folder:
            return

        if not is_git_repository(folder):
            messagebox.showwarning(
                "Repositório inválido",
                "A pasta selecionada não parece ser um repositório Git válido."
            )
            return

        repo_name = os.path.basename(folder)
        self.repositories[repo_name] = folder
        self.selected_repo_path = folder

        repo_names = list(self.repositories.keys())
        self.top_bar.set_repositories(repo_names, repo_name)

        try:
            current_branch = get_current_branch(folder)

            self.sync_branch_ui(current_branch)
            self.set_status(f"Repositório selecionado: {repo_name} ({folder})")

        except GitServiceError as exc:
            messagebox.showerror("Erro Git", str(exc))

    def handle_branch_selected(self, branch_name: str):
        self.perform_branch_checkout(branch_name)

    def handle_top_branch_changed(self, branch_name: str):
        if self.is_updating_branch_ui:
            return
        self.perform_branch_checkout(branch_name)
