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
    - Checkout de branch (se houver alterações que impeçam a troca, oferece guardá-las em stash;
      o stash **não é reaplicado sozinho**: use Aplicar ou Pop na lista de Stashes, e não Descartar)
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
- ⚙️ **Painel de ações** (ícone de ações do topo), no tema do app, com ícones e os grupos à vista:
    - **Sincronizar:** Fetch (todos os remotos, com prune) e Pull com rebase (com `--autostash`)
    - **Integrar:** Merge e Rebase de uma branch, Cherry-pick e Revert de um commit (o commit é
      escolhido na própria busca). Se parar em conflito, o app avisa e o painel mostra no topo
      **Continuar** e **Abortar** a operação em andamento
    - **Branches, tags e histórico:** renomear a branch atual, limpar branches já mescladas,
      **Gerenciar tags** (criar, enviar e apagar, locais e remotas) e o **Reflog**, com o
      histórico do HEAD, ver commit, criar branch no ponto e voltar a ele
    - O painel fecha ao escolher uma ação, com Esc ou ao clicar fora dele. Ele complementa a
      barra do topo e não repete o que ela já faz. **Undo** desfaz o
      último commit (mantém as alterações em stage) e **Redo** o traz de volta; o Redo só vale
      logo depois de um Undo (com outro commit no meio, use o Reflog). O botão **Terminal** do
      topo abre o terminal na pasta do repositório
    - **Repositório:** abrir o repositório ou a branch no GitHub, copiar a URL, abrir no editor
      (`AUTOMATION_EDITOR` define qual; o padrão é o VS Code), clonar e inicializar repositórios
- 📐 **Barra do topo responsiva:** em janelas estreitas os botões que não cabem (Branch, Delete
  Branch, Stash, Pop, Open PR, Merge PR e Terminal) vão para o menu **⋯**, que só aparece quando
  há algo escondido
- 💬 **Tooltips** em todos os botões da barra do topo: ao passar o mouse aparece o nome da função
  (útil nos botões só de ícone e no menu ⋯)
- 🖥️ **Várias telas** (monitor externo, iPad como tela estendida): popups e menus abrem sobre a
  janela do app, na tela onde o mouse está, e o painel de ações e o menu de perfil ficam presos à
  janela. Os diálogos só aparecem depois de posicionados (evita um quadrado preto parado na tela
  no macOS), e o Deletar Branch é compacto para caber em telas menores
- 🔤 Acentos corretos nas mensagens de commit no Windows (a saída do Git é lida como UTF-8)
- 🛡️ Ações que reescrevem histórico (rebase, desfazer commit, voltar no reflog) são bloqueadas
  em branches protegidas (`main`, `master`, `develop`) e `reset --hard` recusa alterações não
  commitadas, para nada ser perdido
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
│   ├── top_bar.py           # Barra do topo (responsiva, com menu ⋯ para botões escondidos)
│   ├── left_sidebar.py      # Barra lateral (Local, Remote, Pull Requests; Cloud Patches, Issues e Teams são reservados)
│   ├── center_panel.py      # Grafo de commits e HoverTooltip (janela única reaproveitada)
│   ├── window_position.py   # Posição de popups e menus com várias telas
│   ├── right_panel.py       # Arquivos (checkboxes, stage/unstage/descartar), stashes e commit
│   ├── diff_viewer.py       # Janela de diff com cores
│   ├── search_dialog.py     # Busca global (commits, arquivos, branches, PRs, conteúdo)
│   ├── actions_menu.py      # Conteúdo do painel de ações (grupos, rótulos, ícones)
│   ├── actions_panel.py     # Painel flutuante de ações (desenha a partir do actions_menu)
│   ├── actions_controller.py # O que cada ação do painel faz (confirmações, segundo plano, conflitos)
│   ├── reflog_dialog.py     # Histórico do HEAD
│   ├── tags_dialog.py       # Lista de tags (enviar, apagar)
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
│   ├── git_actions_service.py # fetch, merge, rebase, cherry-pick, revert, reflog, tags, clonar...
│   ├── system_service.py    # abrir terminal e editor; links do GitHub
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
│   └── icons/              # ícones da interface (traço fino, #E5E7EB, 64x64) e o logo do GitHub
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

Ctrl+C no terminal (ou o botão Stop do IDE) encerra o app sem mostrar traceback.

---

## 🔧 Variáveis de ambiente

Todas são opcionais e podem ficar no `.env` da raiz do projeto (lido na inicialização).

| Variável | Para que serve | Padrão |
|---|---|---|
| `GITHUB_CLIENT_ID` | Client ID do OAuth App, necessário para o login com GitHub | — |
| `GITHUB_OAUTH_SCOPES` | Escopos pedidos ao GitHub no login | `repo user:email` |
| `GITHUB_TOKEN` / `GH_TOKEN` | Token usado nas operações de Pull Request quando não há login | — |
| `AUTOMATION_EDITOR` | Comando do editor da ação "Abrir no editor" (ex.: `idea`, `code -n`) | VS Code (`code`) |
| `AUTOMATION_PERF` | `1` liga o registro de desempenho (tempo dos comandos git e da interface) | desligado |
| `AUTOMATION_PERF_LOG` | Arquivo do registro de desempenho | `automation_perf.log` |

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
- [x] Undo / Redo do topo (desfazer e refazer commit)
- [x] Painel de ações: fetch, merge, rebase, cherry-pick, revert, reflog, tags, abrir no GitHub/editor, clonar
- [x] Suporte a várias telas (monitor externo e iPad) no posicionamento de popups e menus
- [x] Barra do topo responsiva com menu ⋯, tooltips nos botões e correção de acentos (UTF-8) no Windows
- [x] Commit e login em segundo plano (sem travar a janela)

### 🔥 Em desenvolvimento
- [ ] Operações de rede fora da thread da UI (evitar travamento da janela)
- [ ] Aumentar a cobertura de testes

### 💡 Futuro
- [ ] Interface ainda mais próxima do GitKraken
- [ ] Terminal integrado dentro da janela (hoje o botão abre o terminal do sistema)

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
