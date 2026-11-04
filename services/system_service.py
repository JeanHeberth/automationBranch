import os
import shlex
import shutil
import subprocess
import sys
from urllib.parse import quote

from services.git_runner import GitServiceError

_LINUX_TERMINALS = ("x-terminal-emulator", "gnome-terminal", "konsole", "xfce4-terminal", "xterm")
_MAC_VSCODE = "Visual Studio Code"


def _spawn(command: list[str], cwd: str | None = None) -> None:
    """Abre um programa externo sem esperar por ele (a janela do app não pode travar)."""
    try:
        subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as exc:
        raise GitServiceError(f"Programa não encontrado: {command[0]}") from exc
    except OSError as exc:
        raise GitServiceError(f"Não foi possível executar {command[0]}: {exc}") from exc


def _check_folder(path: str) -> None:
    if not path or not os.path.isdir(path):
        raise GitServiceError(f"A pasta não existe: {path}")


def open_folder(path: str) -> None:
    """Abre a pasta no Finder, no Explorer ou no gerenciador de arquivos do Linux."""
    _check_folder(path)

    if sys.platform == "darwin":
        _spawn(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - abre a pasta no Explorer; só existe no Windows
    else:
        _spawn(["xdg-open", path])


def open_terminal(path: str) -> None:
    """Abre um terminal já dentro da pasta."""
    _check_folder(path)

    if sys.platform == "darwin":
        _spawn(["open", "-a", "Terminal", path])
    elif sys.platform == "win32":
        _spawn(["cmd.exe", "/c", "start", "cmd.exe"], cwd=path)
    else:
        for terminal in _LINUX_TERMINALS:
            if shutil.which(terminal):
                _spawn([terminal], cwd=path)
                return
        raise GitServiceError("Nenhum terminal encontrado (tentei: " + ", ".join(_LINUX_TERMINALS) + ").")


def open_editor(path: str) -> None:
    """Abre a pasta no editor. AUTOMATION_EDITOR (ex.: "code" ou "idea") tem prioridade;
    sem ela, usa o VS Code."""
    _check_folder(path)

    custom = os.getenv("AUTOMATION_EDITOR", "").strip()
    if custom:
        _spawn([*shlex.split(custom), path])
        return

    if shutil.which("code"):
        _spawn(["code", path])
    elif sys.platform == "darwin":
        _spawn(["open", "-a", _MAC_VSCODE, path])
    else:
        raise GitServiceError(
            "VS Code não encontrado. Instale o comando 'code' ou defina AUTOMATION_EDITOR "
            "com o editor desejado (ex.: AUTOMATION_EDITOR=idea)."
        )


def build_repo_web_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}"


def build_branch_web_url(owner: str, repo: str, branch: str) -> str:
    return f"{build_repo_web_url(owner, repo)}/tree/{quote(branch, safe='/')}"
