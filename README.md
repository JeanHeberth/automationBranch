# 🚀 Automation Branch

Aplicação desktop moderna para gerenciamento de branches Git, inspirada em ferramentas como GitKraken.

Desenvolvida em Python com foco em produtividade, visual moderno e facilidade de uso.

---

## ✨ Funcionalidades

- 📂 Seleção de repositórios locais
- 🌿 Visualização de branches
- 🔄 Ações rápidas:
    - Pull
    - Push
    - Checkout de branch
    - Stash / Pop
- 🧾 Visualização de commits
- 📁 Arquivos alterados
- 🧠 Interface intuitiva estilo ferramentas profissionais

---

## 🖼️ Preview

> (adicione aqui um print da aplicação depois)

---

## 🏗️ Estrutura do Projeto

```text
automationBranch/
├── main.py
├── ui/                     # Camada de interface (CustomTkinter)
│   ├── main_window.py       # Janela principal e orquestração das ações
│   ├── top_bar.py
│   ├── left_sidebar.py
│   ├── center_panel.py
│   ├── right_panel.py
│   ├── profile_popup.py
│   ├── profile_menu.py
│   ├── delete_branch_popup.py
│   └── theme.py
├── services/               # Lógica de negócio (Git CLI + GitHub API)
│   ├── git_runner.py        # Wrapper de subprocess para o Git
│   ├── branch_service.py
│   ├── branch_delete_service.py
│   ├── commit_service.py
│   ├── sync_service.py      # pull / push / stash
│   ├── pull_request_service.py
│   ├── github_auth_service.py
│   └── session_service.py
├── tests/                  # Testes com pytest
├── assets/
│   └── icons/
├── requirements.txt
├── requirements-dev.txt    # Dependências de teste / CI
├── pyproject.toml
└── README.md
```

---

## ⚙️ Tecnologias

- Python 3.10+ (CI testa nas versões 3.10 a 3.13)
- CustomTkinter (UI moderna)
- Pillow (imagens)
- Git CLI (via `subprocess`)
- GitHub REST API (`requests`) para Pull Requests

---

## 🚀 Como rodar o projeto

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/automation-branch.git
cd automation-branch
```

### 2. Configuração do Sistema (Apenas para macOS)
O Python instalado via Homebrew no Mac não acompanha a interface gráfica por padrão. Instale o suporte ao Tkinter antes de continuar (ajuste a versão conforme o seu Python):

```bash
brew install python-tk
```

### 3. Crie e ative o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Execute o projeto

```bash
python main.py
```

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Para ver a cobertura da camada de serviços:

```bash
pytest --cov=services --cov-report=term
```

---

## 📌 Requisitos

- Python 3.10+
- Git instalado na máquina

---

## 🧠 Roadmap

### ✅ Concluído
- [x] Integração real com Git (subprocess)
- [x] Listagem automática de branches (locais e remotas)
- [x] Checkout de branch
- [x] Pull / Push real (com criação de upstream)
- [x] Histórico gráfico de commits
- [x] Integração com GitHub API (abrir e mergear Pull Requests)
- [x] Suporte multi-repositório
- [x] Login via OAuth do GitHub

### 🔥 Em desenvolvimento
- [ ] Operações de rede fora da thread da UI (evitar travamento da janela)
- [ ] Armazenar o token em keychain (`keyring`) em vez de JSON em texto puro
- [ ] Aumentar a cobertura de testes

### 💡 Futuro
- [ ] Interface ainda mais próxima do GitKraken
- [ ] Terminal integrado
- [ ] Desfazer / refazer (undo / redo)

---

## 🤝 Contribuição

Contribuições são bem-vindas!

```bash
# Crie uma branch
git checkout -b minha-feature

# Commit
git commit -m "feat: minha melhoria"

# Push
git push origin minha-feature
```

Abra um Pull Request 🚀

---

## 📄 Licença

Este projeto está sob a licença Jean Heberth Desenvolvimento.

---

## 👨‍💻 Autor

Desenvolvido por **Jean Heberth**
