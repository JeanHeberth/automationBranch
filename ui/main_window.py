import os
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor
import customtkinter as ctk
from tkinter import filedialog, messagebox, TclError

from ui.dialogs import ask_string, ask_text
from ui.top_bar import TopBar
from ui.left_sidebar import LeftSidebar
from ui.center_panel import CenterPanel
from ui.right_panel import RightPanel
from ui.profile_popup import ProfileConnectPopup
from ui.profile_menu import ProfileMenu
from ui.delete_branch_popup import DeleteBranchPopup
from ui.base_branch_popup import BaseBranchPopup
from ui.theme import APP_COLORS

from services.git_runner import GitServiceError
from services.branch_service import (
    is_git_repository,
    get_current_branch,
    checkout_branch,
    create_branch,
)
from services.branch_delete_service import (
    get_deletable_local_branches,
    get_protected_remote_branches,
    get_deletable_remote_branches,
    delete_local_branch,
    delete_remote_branch,
    delete_all_local,
    delete_all_remote,
)
from services.commit_service import (
    stage_all_changes,
    commit_all_changes,
    amend_commit,
    is_last_commit_pushed,
)
from services.branch_delete_service import is_protected
from services import perf
from services.repo_snapshot import collect_repo_snapshot
from services.pull_request_service import (
    list_open_pull_requests,
    create_pull_request,
    merge_pull_request,
    find_open_pull_request_by_head,
)
from services.sync_service import (
    git_pull,
    git_push,
    git_push_force_with_lease,
    git_stash,
    git_stash_pop,
)
from services.auth_service import (
    get_current_session,
    login_with_github,
    login_with_google,
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
        # Evita disparar duas operações Git de rede ao mesmo tempo.
        self._bg_busy = False
        # Identifica a atualização mais recente da UI (descarta resultados atrasados).
        self._sync_token = 0

        self._configure_window_size()
        perf.start_ui_lag_monitor(self)
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
        self.right_panel.set_on_amend(self.handle_amend)

        self.status_label = ctk.CTkLabel(
            self,
            text="Selecione um repositório para começar.",
            anchor="w",
            fg_color=APP_COLORS["topbar"],
            text_color=APP_COLORS["text"],
            corner_radius=0,
            height=28
        )
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="ew")

        self._load_initial_data()
        self._refresh_profile_ui()

    def _configure_window_size(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width = int(screen_width * 0.985)
        height = int(screen_height * 0.92)

        min_width = 980
        min_height = 620

        width = max(width, min_width)
        height = max(height, min_height)

        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min_width, min_height)

    def _configure_grid(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self.grid_columnconfigure(0, weight=0, minsize=205)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=250)

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
        try:
            session = login_with_github()
            self._refresh_profile_ui()
            self.set_status(f"Conta conectada com sucesso via {session['provider']}.")
        except Exception as exc:
            messagebox.showerror("Erro no login GitHub", str(exc))
            self.set_status("Falha ao conectar conta GitHub.")

    def _connect_google(self):
        try:
            login_with_google()
        except NotImplementedError as exc:
            messagebox.showinfo("Google em breve", str(exc))
            self.set_status("Login com Google ainda não implementado.")
        except Exception as exc:
            messagebox.showerror("Erro no login Google", str(exc))
            self.set_status("Falha ao conectar conta Google.")

    def _logout_profile(self):
        logout()
        self._refresh_profile_ui()
        self.set_status("Conta desconectada com sucesso.")

    def _open_delete_branch_popup(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de deletar branches."
            )
            return

        repo_path = self.selected_repo_path

        def work():
            # As duas consultas são independentes: rodam juntas (cada uma abre processos git).
            with ThreadPoolExecutor(max_workers=2) as pool:
                local = pool.submit(get_deletable_local_branches, repo_path)
                remote = pool.submit(get_deletable_remote_branches, repo_path)
                return local.result(), remote.result()

        def show_popup(branches):
            local_branches, remote_branches = branches
            DeleteBranchPopup(
                self,
                local_branches=local_branches,
                remote_branches=remote_branches,
                on_confirm=self._execute_delete_branch
            )

        self._run_in_background(
            work,
            show_popup,
            busy_message="Carregando branches...",
            error_title="Erro ao abrir popup",
            error_status="Falha ao carregar branches.",
        )

    def _execute_delete_branch(self, mode: str, location: str, branch_name: str):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de deletar branches."
            )
            return False

        repo_path = self.selected_repo_path

        def work():
            """Roda em background e devolve (título, mensagem, status) para a UI exibir."""
            if mode == "specific":
                if not branch_name or branch_name == "Nenhuma branch disponível":
                    raise GitServiceError("Selecione uma branch válida.")

                if location == "local":
                    result = delete_local_branch(repo_path, branch_name)
                    return (
                        "Branch deletada",
                        result or f"Branch local '{branch_name}' deletada com sucesso.",
                        f"Branch local deletada com sucesso: {branch_name}",
                    )

                result = delete_remote_branch(repo_path, branch_name)
                return (
                    "Branch deletada",
                    result or f"Branch remota '{branch_name}' deletada com sucesso.",
                    f"Branch remota deletada com sucesso: {branch_name}",
                )

            if location == "local":
                results = delete_all_local(repo_path)
                return (
                    "Branches deletadas",
                    "\n".join(results) if results else "Nenhuma branch local disponível para deleção.",
                    "Deleção em massa local concluída com sucesso.",
                )

            results = delete_all_remote(repo_path)
            return (
                "Branches deletadas",
                "\n".join(results) if results else "Nenhuma branch remota disponível para deleção.",
                "Deleção em massa remota concluída com sucesso.",
            )

        def done(outcome):
            title, message, status = outcome
            self.sync_branch_ui()
            self.set_status(status)
            messagebox.showinfo(title, message)

        self._run_in_background(
            work,
            done,
            busy_message="Deletando branch...",
            error_title="Erro ao deletar branch",
            error_status="Falha ao deletar branch.",
        )
        return True

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def _run_in_background(
        self,
        work,
        on_success,
        *,
        busy_message: str,
        error_title: str,
        error_status: str,
    ):
        """Executa `work()` numa thread separada para não travar a janela.

        `on_success` e o tratamento de erro rodam de volta na thread da UI
        via `self.after`, que é a forma segura de mexer nos widgets do Tkinter.
        """
        if self._bg_busy:
            messagebox.showinfo(
                "Operação em andamento",
                "Aguarde a conclusão da operação Git atual."
            )
            return

        self._bg_busy = True
        self.set_status(busy_message)

        def finish_ok(result):
            self._bg_busy = False
            if not self.winfo_exists():
                return
            on_success(result)

        def finish_err(exc):
            self._bg_busy = False
            if not self.winfo_exists():
                return
            messagebox.showerror(error_title, str(exc))
            self.set_status(error_status)

        def runner():
            try:
                result = work()
            except Exception as exc:  # GitServiceError, erros de rede, etc.
                self._safe_after(lambda e=exc: finish_err(e))
            else:
                self._safe_after(lambda r=result: finish_ok(r))

        threading.Thread(target=runner, daemon=True).start()

    def _safe_after(self, callback):
        """Agenda um callback na thread da UI, ignorando o caso da janela já ter fechado."""
        try:
            self.after(0, callback)
        except (RuntimeError, TclError):
            pass

    def _finish_git_action(self, result, success_status: str, dialog_title: str, default_msg: str):
        self.sync_branch_ui()
        self.set_status(success_status)
        messagebox.showinfo(dialog_title, result or default_msg)

    def _finish_merge(self, result: dict, pr_number: int):
        self.load_pull_requests()
        self.sync_branch_ui()
        self.set_status(f"PR #{pr_number} mergeado com sucesso.")
        messagebox.showinfo(
            "Merge realizado",
            result.get("message", f"PR #{pr_number} mergeado com sucesso.")
        )

    def load_pull_requests(self):
        if not self.selected_repo_path:
            self.left_sidebar.set_pull_requests([])
            return

        # Chamada à API do GitHub: roda em segundo plano para não travar a UI.
        repo_path = self.selected_repo_path

        def apply(prs):
            # Descarta o resultado se a janela fechou ou o repositório mudou.
            if not self.winfo_exists() or self.selected_repo_path != repo_path:
                return
            with perf.timed(f"UI: left_sidebar.set_pull_requests ({len(prs)} PRs, re-render da sidebar)"):
                self.left_sidebar.set_pull_requests(prs)

        def runner():
            try:
                with perf.timed("API GitHub: list_open_pull_requests"):
                    prs = list_open_pull_requests(repo_path)
            except Exception:
                self._safe_after(lambda: apply([]))
            else:
                self._safe_after(lambda: apply(prs))

        threading.Thread(target=runner, daemon=True).start()

    def sync_branch_ui(self, branch_name: str | None = None):
        """Atualiza branches, commits e arquivos alterados sem travar a janela.

        Os comandos git rodam em paralelo numa thread (collect_repo_snapshot); a UI só
        é tocada de volta na thread principal. Se `branch_name` for None, a branch atual
        é descoberta na própria coleta.
        """
        if not self.selected_repo_path:
            return

        repo_path = self.selected_repo_path
        self._sync_token += 1
        token = self._sync_token
        self.set_status("Atualizando dados do repositório...")
        perf.log(f"--- sync_branch_ui iniciado (token {token}) ---")

        def apply(snapshot):
            # Descarta resultado de uma atualização antiga, de outro repositório ou de janela fechada.
            if (
                not self.winfo_exists()
                or token != self._sync_token
                or self.selected_repo_path != repo_path
            ):
                return
            self._apply_snapshot(snapshot)

        def fail(exc):
            if not self.winfo_exists() or token != self._sync_token:
                return
            messagebox.showerror("Erro Git", str(exc))
            self.set_status("Falha ao atualizar dados do repositório.")

        def runner():
            try:
                snapshot = collect_repo_snapshot(repo_path, branch_name)
            except Exception as exc:
                self._safe_after(lambda e=exc: fail(e))
            else:
                self._safe_after(lambda snap=snapshot: apply(snap))

        threading.Thread(target=runner, daemon=True).start()

    def _apply_snapshot(self, snapshot):
        branch_name = snapshot.branch

        with perf.timed("UI: _apply_snapshot (total, thread da UI)"):
            self.is_updating_branch_ui = True
            try:
                with perf.timed("UI: top_bar.set_branches"):
                    self.top_bar.set_branches(snapshot.local_branches, current_branch=branch_name)
                    self.top_bar.set_selected_branch(branch_name)

                with perf.timed(f"UI: left_sidebar.set_branches ({len(snapshot.local_branches)} locais, "
                                f"{len(snapshot.remote_branches)} remotas)"):
                    self.left_sidebar.set_branches(
                        snapshot.local_branches,
                        remote_branches=snapshot.remote_branches,
                        remotes=snapshot.remotes
                    )
                self.left_sidebar.set_selected_branch(branch_name)
                self.left_sidebar.set_footer_message(f"Branch atual: {branch_name}")
                self.left_sidebar.set_viewing_count(len(snapshot.local_branches))
            finally:
                self.is_updating_branch_ui = False

            with perf.timed(f"UI: center_panel commits ({len(snapshot.commit_rows)} linhas)"):
                self.center_panel.set_current_branch(branch_name)
                if snapshot.commit_error:
                    self.center_panel.set_commits(["Erro ao carregar commits.", snapshot.commit_error])
                else:
                    self.center_panel.set_commit_rows(snapshot.commit_rows)

            with perf.timed("UI: right_panel arquivos alterados"):
                if snapshot.changed_files_error:
                    self.right_panel.set_files_grouped([f"Erro: {snapshot.changed_files_error}"], [])
                else:
                    self.right_panel.set_files_grouped(
                        snapshot.changed_files.get("staged", []),
                        snapshot.changed_files.get("unstaged", [])
                    )

            self.load_pull_requests()

    def perform_branch_checkout(self, branch_name: str):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de trocar de branch."
            )
            return

        repo_path = self.selected_repo_path

        def work():
            checkout_branch(repo_path, branch_name)
            return get_current_branch(repo_path)

        def done(current_branch):
            self.sync_branch_ui(current_branch)
            self.set_status(f"Checkout realizado com sucesso para: {current_branch}")

        # O checkout e a consulta da branch atual são processos git (lentos no Windows):
        # rodam em segundo plano para não travar a janela.
        self._run_in_background(
            work,
            done,
            busy_message=f"Trocando para a branch {branch_name}...",
            error_title="Erro no checkout",
            error_status=f"Falha ao trocar para a branch: {branch_name}",
        )

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

    def handle_amend(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de fazer amend."
            )
            return

        repo_path = self.selected_repo_path
        commit_message = self.right_panel.get_commit_message()

        def prepare():
            branch = get_current_branch(repo_path)
            if is_protected(branch):
                return branch, False
            return branch, is_last_commit_pushed(repo_path, branch)

        def after_prepare(info):
            branch, pushed = info

            if is_protected(branch):
                messagebox.showwarning(
                    "Amend bloqueado",
                    f"Não é permitido reescrever commits da branch protegida '{branch}'."
                )
                self.set_status("Amend bloqueado em branch protegida.")
                return

            if pushed and not messagebox.askyesno(
                "Commit já enviado",
                "O último commit já foi enviado ao remoto.\n"
                "O amend reescreve o histórico e exigirá um force push "
                "(--force-with-lease).\n\nDeseja continuar?"
            ):
                self.set_status("Amend cancelado.")
                return

            self._run_in_background(
                lambda: amend_commit(repo_path, commit_message),
                lambda result: self._finish_amend(result, pushed),
                busy_message="Executando amend...",
                error_title="Erro no amend",
                error_status="Falha ao executar amend.",
            )

        self._run_in_background(
            prepare,
            after_prepare,
            busy_message="Verificando último commit...",
            error_title="Erro no amend",
            error_status="Falha ao executar amend.",
        )

    def _finish_amend(self, result, pushed: bool):
        self.sync_branch_ui()
        self.right_panel.clear_commit_message()
        self.set_status("Amend realizado com sucesso.")
        messagebox.showinfo("Amend", result or "Amend realizado com sucesso.")

        if pushed and messagebox.askyesno(
            "Enviar ao remoto",
            "Deseja enviar agora com force push (--force-with-lease)?"
        ):
            repo_path = self.selected_repo_path
            self._run_in_background(
                lambda: git_push_force_with_lease(repo_path),
                lambda res: self._finish_git_action(
                    res, "Force push executado com sucesso.", "Force push",
                    "Force push executado com sucesso."
                ),
                busy_message="Executando force push...",
                error_title="Erro Git",
                error_status="Erro ao executar force push.",
            )

    def _handle_open_pr(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de abrir Pull Request."
            )
            return

        repo_path = self.selected_repo_path
        current_branch = get_current_branch(repo_path)

        if current_branch == "main":
            messagebox.showwarning(
                "Branch inválida",
                "Não faz sentido abrir PR da branch main para ela mesma."
            )
            return

        # 1º passo (rede): verifica se já existe um PR aberto para a branch.
        self._run_in_background(
            lambda: find_open_pull_request_by_head(repo_path, current_branch),
            lambda existing_pr: self._open_pr_after_check(repo_path, current_branch, existing_pr),
            busy_message="Consultando Pull Requests...",
            error_title="Erro ao consultar Pull Requests",
            error_status="Falha ao consultar Pull Requests.",
        )

    def _open_pr_after_check(self, repo_path: str, current_branch: str, existing_pr):
        if existing_pr:
            self.load_pull_requests()
            self.set_status(f"PR já existe para a branch {current_branch}.")
            messagebox.showinfo(
                "Pull Request existente",
                f"PR #{existing_pr['number']} já está aberto.\n\n{existing_pr['title']}\n{existing_pr['url']}"
            )
            return

        try:
            options = get_protected_remote_branches(repo_path, exclude=current_branch)
        except GitServiceError as exc:
            messagebox.showerror("Erro ao listar branches", str(exc))
            return

        base_branch = BaseBranchPopup(self, options).get_selection()
        if not base_branch:
            return

        title = ask_string(
            "Abrir Pull Request",
            "Título do PR:",
            initialvalue=f"{current_branch} -> {base_branch}"
        )
        if not title:
            return

        body = ask_text(
            self,
            "Descrição do PR",
            "Descrição do PR (opcional):",
        )
        if body is None:
            body = ""

        # 2º passo (rede): cria o PR.
        self._run_in_background(
            lambda: create_pull_request(
                repo_path,
                title=title,
                body=body,
                base_branch=base_branch,
                head_branch=current_branch,
            ),
            self._finish_open_pr,
            busy_message="Abrindo Pull Request...",
            error_title="Erro ao abrir PR",
            error_status="Falha ao abrir Pull Request.",
        )

    def _finish_open_pr(self, pr: dict):
        self.load_pull_requests()
        self.set_status(f"PR aberto com sucesso: #{pr['number']}")
        messagebox.showinfo(
            "Pull Request criado",
            f"PR #{pr['number']} criado com sucesso.\n\n{pr['title']}\n{pr['url']}"
        )

    def _handle_merge_pr(self):
        if not self.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de mergear Pull Request."
            )
            return

        repo_path = self.selected_repo_path
        current_branch = get_current_branch(repo_path)

        def query():
            current_pr = find_open_pull_request_by_head(repo_path, current_branch)
            prs = [] if current_pr else list_open_pull_requests(repo_path)
            return current_pr, prs

        # 1º passo (rede): descobre quais PRs estão abertos.
        self._run_in_background(
            query,
            lambda data: self._merge_pr_after_query(repo_path, data[0], data[1]),
            busy_message="Consultando Pull Requests...",
            error_title="Erro ao consultar Pull Requests",
            error_status="Falha ao consultar Pull Requests.",
        )

    def _merge_pr_after_query(self, repo_path: str, current_pr, prs: list):
        pr_title = ""

        if current_pr:
            pr_number = current_pr["number"]
            pr_title = current_pr["title"]
        else:
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
                selected = ask_string(
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

        pr_number = int(pr_number)

        # 2º passo (rede): faz o merge.
        self._run_in_background(
            lambda: merge_pull_request(repo_path, pr_number),
            lambda result: self._finish_merge(result, pr_number),
            busy_message=f"Mesclando PR #{pr_number}...",
            error_title="Erro ao mergear PR",
            error_status="Falha ao mergear Pull Request.",
        )

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

        pr_number = int(pr_number)
        self._run_in_background(
            lambda: merge_pull_request(self.selected_repo_path, pr_number),
            lambda result: self._finish_merge(result, pr_number),
            busy_message=f"Mesclando PR #{pr_number}...",
            error_title="Erro ao mergear PR",
            error_status="Falha ao mergear Pull Request.",
        )

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

        if action_name == "Delete Branch":
            self._open_delete_branch_popup()
            return

        if action_name == "Profile":
            self._open_profile_menu()
            return

        if not self.selected_repo_path and action_name in {"Pull", "Push", "Branch", "Stash", "Pop", "Refresh", "Delete Branch"}:
            messagebox.showwarning(
                "Repositório não selecionado",
                "Selecione um repositório antes de executar ações Git."
            )
            return

        # Pull e Push acessam a rede: rodam em segundo plano.
        if action_name == "Pull":
            self._run_in_background(
                lambda: git_pull(self.selected_repo_path),
                lambda result: self._finish_git_action(
                    result, "Pull executado com sucesso.", "Pull",
                    "Pull executado com sucesso."
                ),
                busy_message="Executando pull...",
                error_title="Erro Git",
                error_status="Erro ao executar ação: Pull",
            )
            return

        if action_name == "Push":
            self._run_in_background(
                lambda: git_push(self.selected_repo_path),
                lambda result: self._finish_git_action(
                    result, "Push executado com sucesso.", "Push",
                    "Push executado com sucesso."
                ),
                busy_message="Executando push...",
                error_title="Erro Git",
                error_status="Erro ao executar ação: Push",
            )
            return

        if action_name == "Branch":
            branch_name = (ask_string("Criar branch", "Digite o nome da nova branch:") or "").strip()
            if not branch_name:
                return

            repo_path = self.selected_repo_path

            def create():
                result = create_branch(repo_path, branch_name)
                return result, get_current_branch(repo_path)

            def created(outcome):
                result, current_branch = outcome
                self.sync_branch_ui(current_branch)
                self.set_status(f"Branch criada com sucesso: {current_branch}")
                messagebox.showinfo("Nova branch", result or f"Branch '{current_branch}' criada com sucesso.")

            self._run_in_background(
                create,
                created,
                busy_message="Criando branch...",
                error_title="Erro Git",
                error_status="Erro ao executar ação: Branch",
            )
            return

        if action_name in {"Stash", "Pop"}:
            repo_path = self.selected_repo_path
            is_stash = action_name == "Stash"
            success = "Stash executado com sucesso." if is_stash else "Stash pop executado com sucesso."

            def stashed(result):
                self.sync_branch_ui()
                self.set_status(success)
                messagebox.showinfo(action_name, result or success)

            self._run_in_background(
                (lambda: git_stash(repo_path)) if is_stash else (lambda: git_stash_pop(repo_path)),
                stashed,
                busy_message="Executando stash..." if is_stash else "Executando stash pop...",
                error_title="Erro Git",
                error_status=f"Erro ao executar ação: {action_name}",
            )
            return

        try:
            if action_name == "Refresh":
                self.sync_branch_ui()
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

        except ValueError as exc:
            messagebox.showwarning("Entrada inválida", str(exc))
            self.set_status(f"Erro ao executar ação: {action_name}")
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
            self.sync_branch_ui()
            self.set_status(f"Repositório selecionado: {repo_name} ({folder})")

        except GitServiceError as exc:
            messagebox.showerror("Erro Git", str(exc))

    def handle_branch_selected(self, branch_name: str):
        self.perform_branch_checkout(branch_name)

    def handle_top_branch_changed(self, branch_name: str):
        if self.is_updating_branch_ui:
            return
        self.perform_branch_checkout(branch_name)