from __future__ import annotations
import os
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont

class WordSearchRenderer:
    BACKGROUND_COLOR = (255, 255, 255)
    GRID_COLOR = (30, 30, 30)
    TEXT_COLOR = (0, 0, 0)
    ANSWER_HIGHLIGHT_COLOR = (220, 240, 255)

    def __init__(self, wordsearch, cell_size: int = 40, padding: int = 25):
        self.wordsearch = wordsearch
        self.cell_size = cell_size
        self.padding = padding
        try:
            self.font = ImageFont.truetype("arial.ttf", 24)
        except Exception:
            self.font = ImageFont.load_default()
        self.image_width = padding * 2 + self.wordsearch.size * cell_size
        self.image_height = padding * 2 + self.wordsearch.size * cell_size

    def generate_image(self, filename: str, answers: bool = False, dpi: int = 300):
        image = Image.new("RGB", (self.image_width, self.image_height), self.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)

        if answers:
            self._draw_answers(draw)
        self._draw_grid(draw)

        out_dir = os.path.dirname(filename)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        image.save(filename, dpi=(dpi, dpi))
        print(f"🖼️  Imagem '{os.path.basename(filename)}' gerada com sucesso!")

    # --- helpers de texto (compatível Pillow ≥10) ---
    def _text_size(self, draw: ImageDraw.ImageDraw, text: str) -> Tuple[int, int]:
        try:
            l, t, r, b = draw.textbbox((0, 0), text, font=self.font)
            return (r - l, b - t)
        except Exception:
            if hasattr(self.font, "getbbox"):
                l, t, r, b = self.font.getbbox(text)
                return (r - l, b - t)
            return (len(text) * max(6, getattr(self.font, "size", 12) // 2), getattr(self.font, "size", 12))

    def _draw_grid(self, draw: ImageDraw.ImageDraw):
        for r in range(self.wordsearch.size):
            for c in range(self.wordsearch.size):
                x0 = self.padding + c * self.cell_size
                y0 = self.padding + r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                draw.rectangle([x0, y0, x1, y1], outline=self.GRID_COLOR, width=1)

                ch = self.wordsearch.grid[r][c]
                if ch:
                    w, h = self._text_size(draw, ch)
                    tx = x0 + (self.cell_size - w) / 2
                    ty = y0 + (self.cell_size - h) / 2
                    draw.text((tx, ty), ch, fill=self.TEXT_COLOR, font=self.font)

    def _dir_from_arrow(self, arrow: str) -> Tuple[int, int]:
        mapping = {"→": (0, 1), "←": (0, -1), "↓": (1, 0), "↑": (-1, 0),
                   "↘": (1, 1), "↖": (-1, -1), "↙": (1, -1), "↗": (-1, 1)}
        return mapping.get(arrow, (0, 0))

    def _find_word_start(self, word: str, dr: int, dc: int):
        n = self.wordsearch.size
        grid = self.wordsearch.grid
        L = len(word)
        for r in range(n):
            for c in range(n):
                er = r + (L - 1) * dr
                ec = c + (L - 1) * dc
                if not (0 <= er < n and 0 <= ec < n):
                    continue
                ok = True
                for i, ch in enumerate(word):
                    rr = r + i * dr
                    cc = c + i * dc
                    if grid[rr][cc] != ch:
                        ok = False; break
                if ok:
                    return (r, c)
        return None

    def _draw_answers(self, draw: ImageDraw.ImageDraw):
        for word, info in self.wordsearch.placed_words.items():
            if isinstance(info, dict):
                r = info.get('r'); c = info.get('c'); dr = info.get('dr'); dc = info.get('dc')
                if None in (r, c, dr, dc):  # defensivo
                    continue
            else:
                # compat.: formato antigo com seta
                arrow = str(info)
                dr, dc = self._dir_from_arrow(arrow)
                if (dr, dc) == (0, 0):
                    continue
                start = self._find_word_start(word, dr, dc)
                if start is None:
                    continue
                r, c = start

            for i in range(len(word)):
                rr = r + i * dr; cc = c + i * dc
                x0 = self.padding + cc * self.cell_size
                y0 = self.padding + rr * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                draw.rectangle([x0, y0, x1, y1], fill=self.ANSWER_HIGHLIGHT_COLOR)
