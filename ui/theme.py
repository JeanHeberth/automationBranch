from PIL import Image
import customtkinter as ctk
import os

APP_COLORS = {
    "bg": "#1d2128",
    "topbar": "#2b2f38",
    "sidebar": "#21252d",
    "panel": "#21252d",
    "text": "#e8ecf1",
    "muted": "#9aa3b2",
    "accent": "#3b82f6",
    "border": "#3a4050",
}

ICON_PATH = "assets/icons"


def load_icon(name: str, size=(18, 18)):
    path = os.path.join(ICON_PATH, name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Ícone não encontrado: {path}")

    image = Image.open(path)
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)