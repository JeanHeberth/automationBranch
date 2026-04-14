import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from services.git_service import (
    get_local_branches,
    get_current_branch,
    get_recent_commits,
    is_git_repository,
    checkout_branch,
    GitServiceError,
)

from ui.top_bar import TopBar
from ui.left_sidebar import LeftSidebar
from ui.center_panel import CenterPanel
from ui.right_panel import RightPanel
from ui.theme import APP_COLORS

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Automation Branch")
        self.configure(fg_color=APP_COLORS["bg"])

        self.selected_repo_path: str | None = None
        self.repositories: dict[str, str] = {}

        self._configure_window_size()
        self._configure_grid()

        self.top_bar = TopBar(
            self,
            on_select_repo=self.handle_select_repository,
            on_action=self.handle_top_action,
            on_branch_change=self.handle_top_branch_changed
        )

        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="nsew")

        self.left_sidebar = LeftSidebar(self, on_branch_select=self.handle_branch_selected)
        self.left_sidebar.grid(row=1, column=0, sticky="nsew")
        self.left_sidebar.grid_propagate(False)

        self.center_panel = CenterPanel(self)
        self.center_panel.grid(row=1, column=1, sticky="nsew")

        self.right_panel = RightPanel(self)
        self.right_panel.grid(row=1, column=2, sticky="nsew")

        self.status_label = ctk.CTkLabel(
            self,
            text="Projeto carregado com sucesso.",
            anchor="w",
            fg_color=APP_COLORS["topbar"],
            text_color=APP_COLORS["text"],
            corner_radius=0,
            height=32
        )
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="ew")

        self._load_initial_data()

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
        self.left_sidebar.set_branches(["main", "develop", "feature/ui-topbar"])
        self.center_panel.set_commits([
            "// WIP",
            "Merge pull request #41 alterando-arquivo",
            "Criado arquivo .yml",
            "Merge pull request #40 criando-sse",
            "criado um server.address",
            "Merge pull request #39 CAE-36",
        ])
        self.right_panel.set_files([
            "src/test/java/.../DepartamentoServiceTest.java"
        ])

    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def handle_top_action(self, action_name: str):
        self.set_status(f"Ação executada: {action_name}")

        if action_name == "Terminal":
            messagebox.showinfo("Terminal", "Depois vamos conectar isso ao terminal real.")
        elif action_name == "Pull":
            messagebox.showinfo("Pull", "Depois vamos conectar ao git pull real.")
        elif action_name == "Push":
            messagebox.showinfo("Push", "Depois vamos conectar ao git push real.")
        elif action_name == "Branch":
            messagebox.showinfo("Branch", "Depois vamos conectar à criação de branch real.")
        elif action_name == "Stash":
            messagebox.showinfo("Stash", "Depois vamos conectar ao git stash real.")
        elif action_name == "Pop":
            messagebox.showinfo("Pop", "Depois vamos conectar ao git stash pop real.")
        elif action_name == "Undo":
            messagebox.showinfo("Undo", "Função de desfazer ainda será implementada.")
        elif action_name == "Redo":
            messagebox.showinfo("Redo", "Função de refazer ainda será implementada.")
        elif action_name == "Actions":
            messagebox.showinfo("Actions", "Menu de ações extras ainda será implementado.")
        elif action_name == "Search":
            messagebox.showinfo("Search", "Busca ainda será implementada.")
        elif action_name == "Profile":
            messagebox.showinfo("Profile", "Perfil ainda será implementado.")
        elif action_name == "Refresh":
            messagebox.showinfo("Refresh", "Atualização ainda será implementada.")

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

            self.right_panel.set_files([
                ".git/config",
                ".git/HEAD",
            ])

            self.set_status(f"Repositório selecionado: {repo_name} ({folder})")

        except GitServiceError as exc:
            messagebox.showerror("Erro Git", str(exc))

    def handle_branch_selected(self, branch_name: str):
        self.set_status(f"Branch selecionada: {branch_name}")

        current_branches = self.left_sidebar.all_branches[:] if self.left_sidebar.all_branches else [branch_name]

        self.top_bar.set_branches(current_branches, current_branch=branch_name)
        self.top_bar.set_selected_branch(branch_name)
        self.left_sidebar.set_selected_branch(branch_name)
        self.left_sidebar.set_footer_message(f"Branch selecionada: {branch_name}")

        self.load_commits_for_branch(branch_name)

        self.right_panel.set_files([
            "ui/left_sidebar.py",
            "ui/main_window.py",
            "services/git_service.py",
        ])

    def handle_top_branch_changed(self, branch_name: str):
        self.perform_branch_checkout(branch_name)

    def load_commits_for_branch(self, branch_name: str):
        if not self.selected_repo_path:
            self.center_panel.set_commits([
                "Nenhum repositório selecionado."
            ])
            return

        try:
            commits = get_recent_commits(self.selected_repo_path, branch_name, limit=15)

            if not commits:
                self.center_panel.set_commits([
                    f"Nenhum commit encontrado para a branch {branch_name}."
                ])
            else:
                self.center_panel.set_commits(commits)

        except GitServiceError as exc:
            self.center_panel.set_commits([
                "Erro ao carregar commits.",
                str(exc)
            ])

    def sync_branch_ui(self, branch_name: str):
        if not self.selected_repo_path:
            return

        branches = get_local_branches(self.selected_repo_path)

        self.top_bar.set_branches(branches, current_branch=branch_name)
        self.top_bar.set_selected_branch(branch_name)

        self.left_sidebar.set_branches(branches)
        self.left_sidebar.set_selected_branch(branch_name)
        self.left_sidebar.set_footer_message(f"Branch atual: {branch_name}")
        self.left_sidebar.set_viewing_count(len(branches))

        self.load_commits_for_branch(branch_name)

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

            self.right_panel.set_files([
                "services/git_service.py",
                "ui/main_window.py",
                ".git/HEAD",
            ])

            self.set_status(f"Checkout realizado com sucesso para: {current_branch}")

        except GitServiceError as exc:
            messagebox.showerror("Erro no checkout", str(exc))
            self.set_status(f"Falha ao trocar para a branch: {branch_name}")
