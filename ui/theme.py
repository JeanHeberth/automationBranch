from PIL import Image
import customtkinter as ctk
import os

APP_COLORS = {
    # Backgrounds
    "bg": "#0F172A",
    "background": "#0F172A",
    "panel": "#111827",
    "topbar": "#1F2937",
    "sidebar": "#111827",

    # Texto
    "text": "#E5E7EB",
    "muted": "#9CA3AF",

    # Azul principal
    "primary": "#2563EB",
    "primary_hover": "#3B82F6",
    "accent": "#1EC8FF",

    # Estados
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",

    # Neutros
    "border": "#374151",
    "hover": "#374151",
}

ICON_PATH = "assets/icons"


def load_icon(name: str, size=(18, 18)):
    path = os.path.join(ICON_PATH, name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Ícone não encontrado: {path}")

    image = Image.open(path)
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)