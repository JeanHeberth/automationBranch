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
    - Checkout de branch (se houver alterações que impeçam a troca, oferece guardá-las em stash)
    - Stash / Pop
- 🧾 Visualização de commits (histórico gráfico)
- ☑️ **Commit e amend por seleção de arquivos**: cada arquivo alterado tem um checkbox (todos
  marcados por padrão) e há "Selecionar todos". Só o que está marcado entra no commit; o stage
  dos demais fica intacto. Renomeações são tratadas por completo
- 🔍 **Diff por arquivo**: clique no nome para ver o diff (staged, não staged ou arquivo novo),
  com `+` e `-` coloridos
- ➕ **Stage / unstage / descartar por arquivo**: botões `+`, `−` e `✕` em cada item
  (descartar pede confirmação e é irreversível)
- 📦 **Stashes**: botão Stash guarda só os arquivos marcados (inclui arquivos novos); lista no
  painel com diff, Aplicar, Pop e Descartar. Conflito ao reaplicar mantém o stash e avisa
- 🔎 **Busca global** (lupa do topo ou `Cmd+K` / `Ctrl+K`):
    - **Commits** em todas as branches, por mensagem, autor, hash ou **código** ("quem adicionou ou
      removeu este texto?", `git log -S`); o resultado abre o diff do commit
    - **Arquivos** por nome ou caminho, com o histórico do arquivo (seguindo renomeações)
    - **Branches** locais e remotas; escolher faz o checkout (remotas criam a branch local)
    - **PRs** abertos, mergeados e fechados, por número (`#12`), título, branch ou autor; escolher
      abre o PR no navegador
    - **Conteúdo** dos arquivos (`git grep`, ignora binários e o `.gitignore`); escolher abre o
      arquivo na linha encontrada
- ✏️ Amend com proteção de branch protegida e force push guiado (`--force-with-lease`)
- 🔀 Pull Requests: abrir, acompanhar o estado dos checks e mergear (inclusive merge automático
  quando os checks passam). Dá para abrir PR a partir de qualquer branch, inclusive `develop → main`;
  só `main` e `master` são bloqueadas como origem. O app nunca apaga a branch de origem no merge
- 🔐 Login com GitHub (Device Flow), com token guardado no cofre do sistema
- ⚡ Commit, stash, login e demais operações Git rodam em segundo plano, sem travar a janela
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
│   ├── right_panel.py       # Arquivos (checkboxes, stage/unstage/descartar), stashes e commit
│   ├── diff_viewer.py       # Janela de diff com cores
│   ├── search_dialog.py     # Busca global (commits, arquivos, branches, PRs, conteúdo)
│   ├── file_viewer.py       # Arquivo com número de linha e linha destacada
│   ├── profile_popup.py     # Janela "Conectar conta"
│   ├── profile_menu.py
│   ├── device_login_dialog.py  # Código do Device Flow do GitHub
│   ├── delete_branch_popup.py
│   ├── base_branch_popup.py # Escolha da branch de destino ao abrir um PR
│   ├── dialogs.py           # Diálogos de texto (título e descrição do PR, stash)
│   └── theme.py
├── services/               # Lógica de negócio (Git CLI + GitHub API)
│   ├── git_runner.py        # Wrapper de subprocess para o Git
│   ├── branch_service.py
│   ├── branch_delete_service.py
│   ├── commit_service.py    # commit/amend por seleção, diff, stage/unstage/descartar
│   ├── stash_service.py     # criar, listar, aplicar, pop e descartar stashes
│   ├── search_service.py    # busca de commits, arquivos, branches e conteúdo (git grep)
│   ├── repo_snapshot.py     # coleta em paralelo o que a UI precisa redesenhar
│   ├── sync_service.py      # pull / push
│   ├── pull_request_service.py  # PRs: abrir, listar, checks, merge, busca
│   ├── auth_service.py
│   ├── github_auth_service.py  # login via Device Flow do GitHub
│   ├── session_service.py   # sessão e token (keyring)
│   └── perf.py              # medição de desempenho (AUTOMATION_PERF=1)
├── tests/                  # Testes com pytest, usando repositórios Git reais e temporários
├── assets/
│   └── icons/              # ícones da interface (inclui o logo do GitHub)
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
- `keyring` para guardar o token no cofre do sistema (Keychain, Credential Locker, Secret Service)
- `python-dotenv` para ler o `.env`

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

### 5. Configure o login com GitHub (opcional)

Crie um arquivo `.env` na raiz do projeto com o Client ID do seu OAuth App
(veja [Login com GitHub](#-login-com-github)):

```env
GITHUB_CLIENT_ID=seu_client_id
```

Sem isso o app abre normalmente, mas o botão "Continuar com GitHub" avisa que falta configurar.

### 6. Execute o projeto

```bash
python main.py
```

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes de serviços criam repositórios Git de verdade em pastas temporárias (nada toca nos seus
repositórios, no Keychain ou no seu `session.json`), e a API do GitHub é simulada.

Para rodar um arquivo ou um teste específico:

```bash
pytest tests/test_search_service.py
pytest -k "stash and pop"
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

## 🔑 Login com GitHub

O login usa o **Device Flow** do GitHub: não precisa de `client_secret` nem de callback local.

### Configuração (uma vez)

1. No GitHub: **Settings → Developer settings → OAuth Apps → New OAuth App**
   (https://github.com/settings/developers).
   - **Application name:** `Automation Branch`
   - **Homepage URL** e **Authorization callback URL:** `http://127.0.0.1`
     (o Device Flow não usa o callback, mas o campo é obrigatório)
2. Marque **Enable Device Flow** (no formulário ou na página do app, salvando em
   **Update application**). Sem isso o login falha com "Device Flow desativado".
3. Copie o **Client ID** (não precisa gerar o Client Secret) e coloque no `.env`:

```env
GITHUB_CLIENT_ID=seu_client_id

# Opcional: escopos pedidos ao GitHub (padrão: "repo user:email")
# GITHUB_OAUTH_SCOPES="repo user:email"
```

O `.env` já está no `.gitignore`. Reinicie o app depois de editá-lo, pois ele só é lido na
inicialização. Se o OAuth App for de uma organização com restrição de acesso a apps, um
administrador precisa aprová-lo na primeira vez.

### Como usar

1. Ícone de perfil → **Conectar conta** → **Continuar com GitHub**.
2. O navegador abre em `github.com/login/device` e o app mostra o código. Use **Copiar código**
   e cole na página do GitHub.
3. Clique em **Authorize**. O app fecha o diálogo sozinho e mostra a conta conectada.
   **Cancelar** interrompe a espera a qualquer momento.

### Onde fica o token

- Em um cofre do sistema, via `keyring`: Keychain (macOS), Credential Locker (Windows) ou
  Secret Service (Linux). O arquivo de sessão guarda só o perfil (nome, e-mail, avatar).
- Sem cofre disponível, cai para o arquivo de sessão com permissão restrita ao usuário (`600`).
- Sessões antigas, com o token em texto puro, são migradas para o cofre automaticamente.
- Pasta de dados: `~/Library/Application Support/AutomationBranch` (macOS),
  `%APPDATA%\AutomationBranch` (Windows) ou `~/.config/AutomationBranch` (Linux).
- No macOS, na primeira leitura o Keychain pode pedir permissão: escolha **Sempre permitir**.

Sem fazer login, o app ainda usa `GITHUB_TOKEN`/`GH_TOKEN` do ambiente (ou do `.env`) para
as operações de Pull Request.

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
- [x] Login via OAuth do GitHub (Device Flow, sem client secret)
- [x] Token guardado no cofre do sistema (Keychain / Credential Locker) via `keyring`
- [x] Commit e amend por seleção de arquivos (checkbox)
- [x] Diff por arquivo
- [x] Stage / unstage / descartar alterações por arquivo
- [x] Stash com lista, diff, aplicar, pop e descartar
- [x] Busca global de commits, arquivos, branches, Pull Requests e conteúdo dos arquivos
- [x] Commit e login em segundo plano (sem travar a janela)

### 🔥 Em desenvolvimento
- [ ] Operações de rede fora da thread da UI (evitar travamento da janela)
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
