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
├── ui/
│   ├── main_window.py
│   ├── top_bar.py
│   ├── left_sidebar.py
│   ├── center_panel.py
│   ├── right_panel.py
│   └── theme.py
├── assets/
│   └── icons/
├── requirements.txt
└── README.md
```

---

## ⚙️ Tecnologias

- Python 3.14+
- CustomTkinter (UI moderna)
- Pillow (imagens)
- Git CLI (em breve integração completa)

---

## 🚀 Como rodar o projeto

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/automation-branch.git
cd automation-branch
```

### 2. Configuração do Sistema (Apenas para macOS)
O Python instalado via Homebrew no Mac não acompanha a interface gráfica por padrão. Instale o suporte ao Tkinter antes de continuar:

```bash
brew install python-tk@3.14
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

## 📌 Requisitos

- Python 3.14+
- Git instalado na máquina

---

## 🧠 Roadmap

### 🔥 Em desenvolvimento
- [ ] Integração real com Git (subprocess)
- [ ] Listagem automática de branches
- [ ] Checkout de branch
- [ ] Pull / Push real
- [ ] Histórico gráfico de commits

### 💡 Futuro
- [ ] Integração com GitHub API
- [ ] Interface ainda mais próxima do GitKraken
- [ ] Suporte multi-repositório
- [ ] Terminal integrado

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
