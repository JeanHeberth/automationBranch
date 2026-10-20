from pathlib import Path

from PIL import Image, ImageOps
import customtkinter as ctk
import os

APP_COLORS = {
    "bg": "#0F172A",
    "background": "#0F172A",
    "panel": "#111827",
    "topbar": "#1F2937",
    "sidebar": "#111827",

    "text": "#E5E7EB",
    "muted": "#9CA3AF",

    "primary": "#2563EB",
    "primary_hover": "#3B82F6",
    "accent": "#1EC8FF",

    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",

    "border": "#374151",
    "hover": "#374151",
}

# Resolvido a partir da localização deste arquivo, não do diretório de trabalho:
# assim os ícones são encontrados mesmo rodando o app de outra pasta.
ICON_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "icons")
_ICON_CACHE: dict[tuple[str, tuple[int, int]], ctk.CTkImage] = {}


def _crop_transparent_area(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()

    if not bbox:
        return image

    return image.crop(bbox)


def _prepare_icon(image: Image.Image, size: tuple[int, int], padding: int = 2) -> Image.Image:
    image = image.convert("RGBA")
    image = _crop_transparent_area(image)

    target_w, target_h = size
    inner_w = max(target_w - (padding * 2), 1)
    inner_h = max(target_h - (padding * 2), 1)

    fitted = ImageOps.contain(image, (inner_w, inner_h))

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (target_w - fitted.width) // 2
    y = (target_h - fitted.height) // 2
    canvas.paste(fitted, (x, y), fitted)

    return canvas


def _blank_icon(size: tuple[int, int]) -> ctk.CTkImage:
    blank = Image.new("RGBA", size, (0, 0, 0, 0))
    return ctk.CTkImage(light_image=blank, dark_image=blank, size=size)


def load_icon(name: str, size=(18, 18), padding: int = 2):
    cache_key = (name, size)

    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    path = os.path.join(ICON_PATH, name)

    if not os.path.exists(path):
        # Degrada para um ícone vazio em vez de derrubar a janela inteira.
        print(f"[theme] Ícone não encontrado, usando espaço vazio: {path}")
        icon = _blank_icon(size)
        _ICON_CACHE[cache_key] = icon
        return icon

    try:
        image = Image.open(path)
        prepared = _prepare_icon(image, size=size, padding=padding)
        icon = ctk.CTkImage(light_image=prepared, dark_image=prepared, size=size)
    except (OSError, ValueError) as exc:
        print(f"[theme] Falha ao carregar o ícone {path}: {exc}")
        icon = _blank_icon(size)

    _ICON_CACHE[cache_key] = icon
    return icon
