import time
import webbrowser
from tkinter import filedialog, messagebox

from services import git_actions_service as git_actions
from services import system_service as system
from services.branch_delete_service import delete_local_branch, is_protected
from services.branch_service import get_current_branch, get_local_and_remote_branches, is_git_repository
from services.commit_service import is_last_commit_pushed
from services.git_runner import GitServiceError
from services.pull_request_service import get_repo_owner_and_name
from services.sync_service import git_pull
from ui.actions_panel import ActionsPanel
from ui.base_branch_popup import BaseBranchPopup
from ui.dialogs import ask_string
from ui.reflog_dialog import ReflogDialog
from ui.search_dialog import SearchDialog
from ui.tags_dialog import TagsDialog

MAX_LISTED_BRANCHES = 15


class ActionsController:
    """Ações do menu do ícone de ações. Cada ação roda o git em segundo plano e devolve o
    resultado à janela principal (`window`), que cuida de status, atualização e threads."""

    def __init__(self, window):
        self.w = window
        self._panel = None
        self._panel_closed_at = 0.0
        self._tags_dialog = None

    # ---------- menu ----------

    def handlers(self) -> dict:
        return {
            "fetch": self.fetch,
            "pull_rebase": self.pull_rebase,
            "merge": self.merge,
            "rebase": self.rebase,
            "cherry_pick": self.cherry_pick,
            "revert": self.revert,
            "reflog": self.reflog,
            "rename_branch": self.rename_branch,
            "clean_merged": self.clean_merged,
            "manage_tags": self.manage_tags,
            "open_repo_web": self.open_repo_web,
            "open_branch_web": self.open_branch_web,
            "copy_repo_url": self.copy_repo_url,
            "open_editor": self.open_editor,
            "clone": self.clone,
            "init": self.init_repo,
            "continue": self.continue_operation,
            "abort": self.abort_operation,
        }

    def show_menu(self):
        # Clicar no botão com o painel aberto: o foco sai do painel (que fecha) antes do clique
        # chegar aqui; sem esta guarda o painel fecharia e reabriria na mesma hora.
        if time.monotonic() - self._panel_closed_at < 0.3:
            return

        repo = self.w.selected_repo_path
        # Leitura de arquivos dentro do .git (sem abrir processo): barato o bastante para o clique.
        operation = git_actions.get_operation_in_progress(repo) if repo else None

        self._panel = ActionsPanel(
            self.w, self.w.top_bar.actions_btn, self.handlers(), operation, on_close=self._on_panel_closed
        )

    def _on_panel_closed(self):
        self._panel_closed_at = time.monotonic()
        self._panel = None

    # ---------- utilitários ----------

    def _repo(self, action: str) -> str | None:
        if not self.w.selected_repo_path:
            messagebox.showwarning(
                "Repositório não selecionado",
                f"Selecione um repositório antes de {action}."
            )
            return None
        return self.w.selected_repo_path

    def _run(self, work, on_success, busy: str, error_title: str):
        self.w._run_in_background(
            work,
            on_success,
            busy_message=busy,
            error_title=error_title,
            error_status=f"Falha: {error_title.lower()}.",
        )

    def _refresh(self, status: str):
        self.w.sync_branch_ui()
        self.w.set_status(status)

    def _simple(self, repo: str, work, status: str, busy: str, error_title: str):
        """Executa `work` e, ao terminar, atualiza a tela e mostra o status."""
        self._run(work, lambda _result: self._refresh(status), busy, error_title)

    @staticmethod
    def _branch_options(local: list[str], remote: list[str], exclude: str) -> list[str]:
        local_set = set(local)
        options = [name for name in local if name != exclude]
        options += [name for name in remote if name.split("/", 1)[-1] not in local_set]
        return options

    def _integrate(self, repo: str, work, success_status: str, title: str, busy: str):
        """Roda uma operação que pode parar em conflito (merge, rebase, cherry-pick, revert...)."""

        def wrapped():
            try:
                return {"output": work()}
            except GitServiceError as exc:
                operation = git_actions.get_operation_in_progress(repo)
                if operation:
                    return {"conflict": str(exc), "operation": operation}
                raise

        self._run(wrapped, lambda result: self._after_integration(result, success_status, title), busy, f"Erro: {title}")

    def _after_integration(self, result: dict, success_status: str, title: str):
        self.w.sync_branch_ui()

        if "conflict" in result:
            operation = result["operation"]
            self.w.set_status(f"{title}: parou em conflito ({operation} em andamento).")
            if messagebox.askyesno(
                f"{title}: conflitos",
                f"{result['conflict']}\n\nResolva os conflitos nos arquivos, coloque-os em stage e use "
                f"Ações > Continuar {operation}.\n\nDeseja abortar o {operation} agora?",
                icon="warning",
            ):
                self.abort_operation()
            return

        self.w.set_status(success_status)
        if result["output"]:
            messagebox.showinfo(title, result["output"])

    # ---------- sincronizar ----------

    def fetch(self):
        repo = self._repo("buscar (fetch)")
        if not repo:
            return
        self._run(
            lambda: git_actions.fetch_all(repo),
            lambda message: self._refresh(message),
            "Executando fetch...", "Erro no fetch",
        )

    def pull_rebase(self):
        repo = self._repo("fazer pull com rebase")
        if not repo:
            return
        self._integrate(
            repo, lambda: git_pull(repo, rebase=True),
            "Pull com rebase concluído.", "Pull com rebase", "Executando pull com rebase...",
        )

    # ---------- integrar ----------

    def merge(self):
        repo = self._repo("fazer merge")
        if not repo:
            return

        def prepare():
            return get_current_branch(repo), get_local_and_remote_branches(repo)

        def choose(info):
            current, (local, remote) = info
            options = self._branch_options(local, remote, current)
            if not options:
                messagebox.showinfo("Merge", "Não há outra branch para mesclar.")
                return

            branch = BaseBranchPopup(
                self.w, options, title="Merge", label=f"Mesclar na branch '{current}':", confirm_text="Mesclar"
            ).get_selection()
            if not branch:
                return

            if is_protected(current) and not messagebox.askyesno(
                "Branch protegida",
                f"Você está na branch protegida '{current}'.\nMesclar '{branch}' nela mesmo assim?",
                icon="warning",
            ):
                return

            self._integrate(
                repo, lambda: git_actions.merge_branch(repo, branch),
                f"'{branch}' mesclada em '{current}'.", "Merge", "Executando merge...",
            )

        self._run(prepare, choose, "Carregando branches...", "Erro ao listar branches")

    def rebase(self):
        repo = self._repo("fazer rebase")
        if not repo:
            return

        def prepare():
            return get_current_branch(repo), get_local_and_remote_branches(repo)

        def choose(info):
            current, (local, remote) = info

            if is_protected(current):
                messagebox.showwarning(
                    "Rebase bloqueado",
                    f"Não é permitido reescrever o histórico da branch protegida '{current}'."
                )
                return

            options = self._branch_options(local, remote, current)
            if not options:
                messagebox.showinfo("Rebase", "Não há outra branch como destino.")
                return

            branch = BaseBranchPopup(
                self.w, options, title="Rebase", label=f"Rebase de '{current}' sobre:", confirm_text="Continuar"
            ).get_selection()
            if not branch:
                return

            if not messagebox.askyesno(
                "Confirmar rebase",
                f"O rebase reaplica os commits de '{current}' sobre '{branch}' e reescreve o histórico "
                "da branch.\nSe ela já foi enviada ao remoto, será preciso um force push.\n\nContinuar?",
                icon="warning",
            ):
                return

            self._integrate(
                repo, lambda: git_actions.rebase_onto(repo, branch),
                f"Rebase sobre '{branch}' concluído.", "Rebase", "Executando rebase...",
            )

        self._run(prepare, choose, "Carregando branches...", "Erro ao listar branches")

    def _pick_commit(self, repo: str, title: str, on_pick):
        # A busca de commits reaproveitada como seletor: só a aba Commits, e escolher fecha a janela.
        SearchDialog(
            self.w, repo,
            on_open_commit=on_pick,
            on_checkout_branch=lambda *_args: None,
            tabs=("Commits",),
            title=title,
            close_on_pick=True,
        )

    def cherry_pick(self):
        repo = self._repo("fazer cherry-pick")
        if not repo:
            return

        def picked(commit_hash: str, subject: str):
            if not messagebox.askyesno("Cherry-pick", f"Aplicar este commit na branch atual?\n\n{commit_hash}  {subject}"):
                return
            self._integrate(
                repo, lambda: git_actions.cherry_pick(repo, commit_hash),
                f"Cherry-pick de {commit_hash} concluído.", "Cherry-pick", "Executando cherry-pick...",
            )

        self._pick_commit(repo, "Cherry-pick: escolha o commit", picked)

    def revert(self):
        repo = self._repo("fazer revert")
        if not repo:
            return

        def picked(commit_hash: str, subject: str):
            if not messagebox.askyesno(
                "Revert", f"Criar um commit que desfaz este?\n\n{commit_hash}  {subject}"
            ):
                return
            self._integrate(
                repo, lambda: git_actions.revert_commit(repo, commit_hash),
                f"Revert de {commit_hash} concluído.", "Revert", "Executando revert...",
            )

        self._pick_commit(repo, "Revert: escolha o commit", picked)

    def continue_operation(self):
        repo = self._repo("continuar a operação")
        if not repo:
            return
        self._integrate(
            repo, lambda: git_actions.continue_operation(repo),
            "Operação concluída.", "Continuar operação", "Continuando operação...",
        )

    def abort_operation(self):
        repo = self._repo("abortar a operação")
        if not repo:
            return
        self._simple(
            repo, lambda: git_actions.abort_operation(repo),
            "Operação abortada.", "Abortando operação...", "Erro ao abortar",
        )

    # ---------- desfazer e recuperar ----------

    def undo_commit(self):
        repo = self._repo("desfazer o último commit")
        if not repo:
            return

        def prepare():
            branch = get_current_branch(repo)
            if is_protected(branch):
                return {"branch": branch, "protected": True}
            return {
                "branch": branch,
                "protected": False,
                "pushed": is_last_commit_pushed(repo, branch),
                "summary": git_actions.get_last_commit_summary(repo),
            }

        def confirm(info):
            if info["protected"]:
                messagebox.showwarning(
                    "Desfazer bloqueado",
                    f"Não é permitido reescrever o histórico da branch protegida '{info['branch']}'."
                )
                return

            text = (
                f"Desfazer o último commit?\n\n{info['summary']}\n\n"
                "As alterações voltam para o stage, nada é perdido."
            )
            if info["pushed"]:
                text += (
                    "\n\nEsse commit já foi enviado ao remoto: o histórico local vai divergir "
                    "e será preciso um force push."
                )
            if not messagebox.askyesno("Desfazer último commit", text):
                return

            self._run(
                lambda: git_actions.undo_last_commit(repo),
                lambda summary: self._refresh(f"Commit desfeito: {summary}"),
                "Desfazendo commit...", "Erro ao desfazer commit",
            )

        self._run(prepare, confirm, "Verificando último commit...", "Erro ao desfazer commit")

    def redo_commit(self):
        repo = self._repo("refazer o commit desfeito")
        if not repo:
            return

        def prepare():
            branch = get_current_branch(repo)
            if is_protected(branch):
                return {"protected": True, "branch": branch}
            return {"protected": False, "target": git_actions.get_redo_target(repo)}

        def confirm(info):
            if info["protected"]:
                messagebox.showwarning(
                    "Refazer bloqueado",
                    f"Não é permitido reescrever o histórico da branch protegida '{info['branch']}'."
                )
                return

            if info["target"] is None:
                messagebox.showinfo(
                    "Refazer",
                    "Não há um \"desfazer commit\" recente para refazer.\n\n"
                    "Para voltar a um ponto anterior, use Ações > Reflog."
                )
                return

            self._run(
                lambda: git_actions.redo_last_undo(repo),
                lambda summary: self._refresh(f"Commit refeito: {summary}"),
                "Refazendo commit...", "Erro ao refazer commit",
            )

        self._run(prepare, confirm, "Verificando o que refazer...", "Erro ao refazer commit")

    def reflog(self):
        repo = self._repo("ver o reflog")
        if not repo:
            return

        holder = {}

        def view(entry: dict):
            self.w._show_commit_diff(entry["hash"], entry["message"])

        def branch_here(entry: dict):
            name = ask_string("Criar branch", f"Nome da nova branch no ponto {entry['hash']}:")
            if not name:
                return
            self._run(
                lambda: git_actions.create_branch_at(repo, name, entry["hash"]),
                lambda _r: self._refresh(f"Branch '{name.strip()}' criada em {entry['hash']}."),
                "Criando branch...", "Erro ao criar branch",
            )

        def reset_here(entry: dict):
            if not messagebox.askyesno(
                "Voltar a este ponto",
                f"Mover a branch atual para {entry['hash']} ({entry['message']})?\n\n"
                "Os commits posteriores saem da branch, mas continuam no reflog.\n"
                "Alterações não commitadas impedem a operação.",
                icon="warning",
            ):
                return

            def done(_result):
                if holder.get("dialog") is not None:
                    holder["dialog"].close()
                self._refresh(f"Branch movida para {entry['hash']}.")

            self._run(
                lambda: git_actions.reset_hard(repo, entry["hash"]), done,
                "Voltando ao ponto escolhido...", "Erro ao voltar ao ponto",
            )

        self._run(
            lambda: git_actions.get_reflog(repo),
            lambda entries: holder.update(dialog=ReflogDialog(self.w, entries, view, branch_here, reset_here)),
            "Carregando reflog...", "Erro ao ler o reflog",
        )

    # ---------- branches e tags ----------

    def rename_branch(self):
        repo = self._repo("renomear a branch")
        if not repo:
            return

        def ask(current: str):
            if is_protected(current):
                messagebox.showwarning(
                    "Renomear bloqueado", f"A branch '{current}' é protegida e não pode ser renomeada."
                )
                return

            new_name = ask_string("Renomear branch", f"Novo nome para '{current}':", initialvalue=current)
            if not new_name or new_name.strip() == current:
                return

            self._run(
                lambda: git_actions.rename_branch(repo, current, new_name),
                lambda message: self._refresh(message),
                "Renomeando branch...", "Erro ao renomear branch",
            )

        self._run(lambda: get_current_branch(repo), ask, "Lendo a branch atual...", "Erro ao ler a branch")

    def clean_merged(self):
        repo = self._repo("limpar branches")
        if not repo:
            return

        def prepare():
            local, _remote = get_local_and_remote_branches(repo)
            return [base for base in ("develop", "main", "master") if base in local]

        def choose_base(bases):
            if not bases:
                messagebox.showinfo("Limpar branches", "Não há branch develop, main ou master para comparar.")
                return

            base = bases[0] if len(bases) == 1 else BaseBranchPopup(
                self.w, bases, title="Limpar branches", label="Remover branches já mescladas em:",
                confirm_text="Buscar",
            ).get_selection()
            if not base:
                return

            self._run(
                lambda: git_actions.get_merged_branches(repo, base),
                lambda branches: confirm_delete(base, branches),
                "Procurando branches mescladas...", "Erro ao listar branches",
            )

        def confirm_delete(base, branches):
            if not branches:
                messagebox.showinfo("Limpar branches", f"Nenhuma branch local está mesclada em '{base}'.")
                return

            listed = "\n".join(f"  • {name}" for name in branches[:MAX_LISTED_BRANCHES])
            if len(branches) > MAX_LISTED_BRANCHES:
                listed += f"\n  … e mais {len(branches) - MAX_LISTED_BRANCHES}"

            if not messagebox.askyesno(
                "Limpar branches",
                f"{len(branches)} branch(es) local(is) já mesclada(s) em '{base}':\n\n{listed}\n\n"
                "Apagar do computador? (As remotas não são tocadas.)",
            ):
                return

            def delete_all():
                deleted, failed = [], []
                for name in branches:
                    try:
                        delete_local_branch(repo, name)
                        deleted.append(name)
                    except GitServiceError as exc:
                        failed.append(f"{name}: {exc}")
                return deleted, failed

            def done(outcome):
                deleted, failed = outcome
                self._refresh(f"{len(deleted)} branch(es) removida(s).")
                if failed:
                    messagebox.showwarning("Limpar branches", "Não foi possível apagar:\n\n" + "\n".join(failed))

            self._run(delete_all, done, "Apagando branches...", "Erro ao apagar branches")

        self._run(prepare, choose_base, "Carregando branches...", "Erro ao listar branches")

    def new_tag(self):
        repo = self._repo("criar uma tag")
        if not repo:
            return

        name = ask_string("Nova tag", "Nome da tag (ex.: v1.0.0):")
        if not name:
            return

        message = ask_string("Nova tag", "Mensagem (opcional; em branco cria uma tag leve):")
        if message is None:
            return

        def created(_result):
            self._reload_tags()
            self.w.set_status(f"Tag '{name.strip()}' criada.")
            if messagebox.askyesno("Enviar tag", f"Tag '{name.strip()}' criada.\nEnviar ao remoto agora?"):
                self._tag_action("push", name.strip())

        self._run(
            lambda: git_actions.create_tag(repo, name, message), created,
            "Criando tag...", "Erro ao criar tag",
        )

    def manage_tags(self):
        repo = self._repo("ver as tags")
        if not repo:
            return

        if self._tags_dialog is not None and self._tags_dialog.winfo_exists():
            self._tags_dialog.focus_force()
            self._reload_tags()
            return

        def show(tags):
            self._tags_dialog = TagsDialog(self.w, tags, on_action=self._tag_action, on_new=self.new_tag)

        self._run(lambda: git_actions.list_tags(repo), show, "Carregando tags...", "Erro ao listar tags")

    def _reload_tags(self):
        repo = self.w.selected_repo_path
        if not repo or self._tags_dialog is None or not self._tags_dialog.winfo_exists():
            return

        def update(tags):
            if self._tags_dialog is not None and self._tags_dialog.winfo_exists():
                self._tags_dialog.set_tags(tags)

        self._run(lambda: git_actions.list_tags(repo), update, "Atualizando tags...", "Erro ao listar tags")

    def _tag_action(self, action: str, name: str):
        repo = self._repo("alterar tags")
        if not repo:
            return

        if action == "push":
            work, busy, status = lambda: git_actions.push_tag(repo, name), "Enviando tag...", f"Tag '{name}' enviada."
        elif action == "delete":
            if not messagebox.askyesno("Apagar tag", f"Apagar a tag local '{name}'?", icon="warning"):
                return
            work, busy, status = lambda: git_actions.delete_tag(repo, name), "Apagando tag...", f"Tag '{name}' apagada."
        else:
            if not messagebox.askyesno(
                "Apagar tag remota", f"Apagar a tag '{name}' do remoto?\nQuem já a baixou continua com ela.", icon="warning"
            ):
                return
            work = lambda: git_actions.delete_remote_tag(repo, name)  # noqa: E731
            busy, status = "Apagando tag remota...", f"Tag '{name}' apagada do remoto."

        def done(_result):
            self.w.set_status(status)
            self._reload_tags()

        self._run(work, done, busy, "Erro na tag")

    # ---------- repositório ----------

    def _web_url(self, repo: str, with_branch: bool):
        def work():
            owner, name = get_repo_owner_and_name(repo)
            if with_branch:
                return system.build_branch_web_url(owner, name, get_current_branch(repo))
            return system.build_repo_web_url(owner, name)

        return work

    def open_repo_web(self):
        repo = self._repo("abrir o repositório")
        if not repo:
            return
        self._run(self._web_url(repo, False), self._open_url, "Montando o link...", "Erro ao abrir no GitHub")

    def open_branch_web(self):
        repo = self._repo("abrir a branch")
        if not repo:
            return
        self._run(self._web_url(repo, True), self._open_url, "Montando o link...", "Erro ao abrir no GitHub")

    def _open_url(self, url: str):
        webbrowser.open(url)
        self.w.set_status(f"Abrindo {url}")

    def copy_repo_url(self):
        repo = self._repo("copiar a URL")
        if not repo:
            return

        def copy(url: str):
            self.w.clipboard_clear()
            self.w.clipboard_append(url)
            self.w.set_status(f"URL copiada: {url}")

        self._run(self._web_url(repo, False), copy, "Montando o link...", "Erro ao copiar a URL")

    def _open_external(self, action, what: str):
        repo = self._repo(what)
        if not repo:
            return
        try:
            action(repo)
        except GitServiceError as exc:
            messagebox.showerror("Erro", str(exc))

    def open_terminal(self):
        self._open_external(system.open_terminal, "abrir o terminal")

    def open_editor(self):
        self._open_external(system.open_editor, "abrir o editor")

    def clone(self):
        url = ask_string("Clonar repositório", "URL do repositório (HTTPS ou SSH):")
        if not url:
            return

        parent = filedialog.askdirectory(title="Pasta onde o repositório será criado")
        if not parent:
            return

        self._run(
            lambda: git_actions.clone_repository(url, parent),
            self._opened_repository,
            "Clonando repositório...", "Erro ao clonar",
        )

    def init_repo(self):
        folder = filedialog.askdirectory(title="Pasta onde criar o repositório")
        if not folder:
            return

        if is_git_repository(folder):
            messagebox.showinfo("Inicializar repositório", "Essa pasta já é um repositório Git. Vou selecioná-la.")
            self._opened_repository(folder)
            return

        if not messagebox.askyesno("Inicializar repositório", f"Criar um repositório Git em:\n{folder}?"):
            return

        self._run(
            lambda: git_actions.init_repository(folder),
            self._opened_repository,
            "Inicializando repositório...", "Erro ao inicializar",
        )

    def _opened_repository(self, folder: str):
        self.w.select_repository(folder)
