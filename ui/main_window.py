import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

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
            on_action=self.handle_top_action
        )
        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="nsew")

        self.left_sidebar = LeftSidebar(self)
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

        git_folder = os.path.join(folder, ".git")
        if not os.path.isdir(git_folder):
            messagebox.showwarning(
                "Repositório inválido",
                "A pasta selecionada não parece ser um repositório Git."
            )
            return

        repo_name = os.path.basename(folder)
        self.repositories[repo_name] = folder
        self.selected_repo_path = folder

        repo_names = list(self.repositories.keys())
        self.top_bar.set_repositories(repo_names, repo_name)

        self.set_status(f"Repositório selecionado: {repo_name} ({folder})")

        self.top_bar.set_branches(["main", "develop", "feature/nova-ui"], "main")
        self.left_sidebar.set_branches(["main", "develop", "feature/nova-ui"])
        self.center_panel.set_commits([
            f"Repositório {repo_name} carregado",
            "Commit de exemplo 1",
            "Commit de exemplo 2",
        ])
        self.right_panel.set_files([
            "README.md",
            "src/main.py",
            "ui/top_bar.py",
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

        git_folder = os.path.join(folder, ".git")
        if not os.path.isdir(git_folder):
            messagebox.showwarning(
                "Repositório inválido",
                "A pasta selecionada não parece ser um repositório Git."
            )
            return

        repo_name = os.path.basename(folder)
        self.repositories[repo_name] = folder
        self.selected_repo_path = folder

        repo_names = list(self.repositories.keys())
        self.top_bar.set_repositories(repo_names, repo_name)

        self.set_status(f"Repositório selecionado: {repo_name} ({folder})")

        # dados temporários até conectarmos com git real
        self.top_bar.set_branches(["main", "develop", "feature/nova-ui"], "main")
        self.left_sidebar.set_branches(["main", "develop", "feature/nova-ui"])
        self.center_panel.set_commits([
            f"Repositório {repo_name} carregado",
            "Commit de exemplo 1",
            "Commit de exemplo 2",
        ])
        self.right_panel.set_files([
            "README.md",
            "src/main.py",
            "ui/top_bar.py",
        ])