from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image, ImageDraw, ImageFont

class CrosswordRenderer:
    """
    Renderizador de palavras-cruzadas (ink-saver):
    - Fundo branco liso
    - Blocos com hachura diagonal (sem preto sólido)
    - Números + setas com gap (evita sobrepor)
    - Letras: no gabarito (answers=True) ou nas posições prefill (answers=False)
    """

    def __init__(
        self,
        crossword,
        clue_generator,
        *,
        cell_size: int = 40,
        padding: int = 25,
        ink_saver: bool = True,
        header_text: Optional[str] = None,
        watermark_text: Optional[str] = None,  # não usado
        corner_pad: int = 2,
        arrow_gap_px: Optional[int] = None,
    ) -> None:
        self.crossword = crossword
        self.clue_gen = clue_generator
        self.cell = int(cell_size)
        self.pad = int(padding)
        self.ink_saver = bool(ink_saver)
        self.header_text = header_text
        self.corner_pad = int(corner_pad)
        self.arrow_gap = 2 if arrow_gap_px is None else int(arrow_gap_px)

        # posições reveladas no exercício
        self.prefilled_positions: Set[Tuple[int, int]] = set()

        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    # ---------- API pública ----------
    def generate_image(self, filename: str, answers: bool = False) -> None:
        grid: List[List[Optional[str]]] = self.crossword.grid
        rows, cols = len(grid), len(grid[0])

        header_h = 0
        header_font = self._get_font(self.cell // 2, prefer="arial")
        if self.header_text:
            header_h = int(self.cell * 0.9)

        W = self.pad * 2 + cols * self.cell
        H = self.pad * 2 + rows * self.cell + header_h

        image = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)

        # Header
        if self.header_text:
            tw, th = self._text_size(draw, self.header_text, header_font)
            draw.text(((W - tw) // 2, self.pad + (header_h - th) // 2),
                      self.header_text, fill=(0, 0, 0), font=header_font)

        ox, oy = self.pad, self.pad + header_h

        # Estilos
        grid_color = (60, 60, 60, 255)
        num_color = (0, 0, 0, 255)
        letter_color = (0, 0, 0, 255)
        hatch_color = (170, 170, 170, 255)

        # Fontes
        num_font = self._get_font(max(10, int(self.cell * 0.33)), prefer="arial")
        arrow_font = self._get_font(max(9, int(self.cell * 0.30)), prefer="arial")
        letter_font = self._get_font(max(12, int(self.cell * 0.55)), prefer="arial")

        # Células (hachura só em blocos)
        for r in range(rows):
            for c in range(cols):
                x0 = ox + c * self.cell
                y0 = oy + r * self.cell
                x1, y1 = x0 + self.cell, y0 + self.cell
                rect = (x0, y0, x1, y1)

                if grid[r][c] is None:
                    self._draw_hatch_cell(image, rect, color=hatch_color, spacing=6, thickness=1)
                # borda
                draw.rectangle(rect, outline=grid_color, width=1)

        # Letras (gabarito ou prefill)
        for r in range(rows):
            for c in range(cols):
                ch = grid[r][c]
                if not ch:
                    continue
                if answers or (r, c) in self.prefilled_positions:
                    x0 = ox + c * self.cell
                    y0 = oy + r * self.cell
                    cx, cy = x0 + self.cell // 2, y0 + self.cell // 2
                    tw, th = self._text_size(draw, ch, letter_font)
                    draw.text((cx - tw // 2, cy - th // 2), ch, fill=letter_color, font=letter_font)

        # Números + setas
        # clue_positions: {(r,c): [{'num': '1', 'dir': 'horizontal'|'vertical'}, ...]}
        starts: Dict[Tuple[int, int], Tuple[str, Set[str]]] = {}
        for (rc, infos) in self.clue_gen.clue_positions.items():
            r, c = rc
            dirs: Set[str] = set()
            num_val: Optional[str] = None
            for info in infos:
                d = (info.get("dir") or "").lower()
                if d in ("horizontal", "across"):
                    dirs.add("across")
                elif d in ("vertical", "down"):
                    dirs.add("down")
                n = info.get("num")
                if n is not None:
                    num_val = str(n)
            if num_val is None:
                continue
            if (r, c) not in starts:
                starts[(r, c)] = (num_val, set())
            starts[(r, c)][1].update(dirs)

        for (r, c), (num_txt, dirs) in starts.items():
            if grid[r][c] is None:
                continue
            x0 = ox + c * self.cell + self.corner_pad
            y0 = oy + r * self.cell + self.corner_pad

            # número
            ntw, nth = self._text_size(draw, num_txt, num_font)
            draw.text((x0, y0), num_txt, fill=num_color, font=num_font)

            # setas
            if "across" in dirs:
                arrow = "→"
                atw, ath = self._text_size(draw, arrow, arrow_font)
                ax = x0 + ntw + self.arrow_gap
                ay = y0
                # não invadir a letra
                ax = min(ax, ox + (c + 1) * self.cell - 1 - atw)
                draw.text((ax, ay), arrow, fill=num_color, font=arrow_font)

            if "down" in dirs:
                arrow = "↓"
                atw, ath = self._text_size(draw, arrow, arrow_font)
                ax = x0
                ay = y0 + nth + self.arrow_gap
                ay = min(ay, oy + (r + 1) * self.cell - 1 - ath)
                draw.text((ax, ay), arrow, fill=num_color, font=arrow_font)

        # Salva (300 DPI)
        image = image.convert("RGB")
        image.save(filename, format="PNG", dpi=(300, 300))

    # ---------- Prefill helpers ----------
    def compute_prefill_first_letters(self, include_across: bool = True, include_down: bool = False) -> Set[Tuple[int, int]]:
        result: Set[Tuple[int, int]] = set()
        for (rc, infos) in self.clue_gen.clue_positions.items():
            r, c = rc
            for info in infos:
                d = (info.get("dir") or "").lower()
                if (d in ("horizontal", "across") and include_across) or (d in ("vertical", "down") and include_down):
                    result.add((r, c))
        return result

    def compute_prefill_percent(self, percent: float = 10.0, seed: Optional[int] = None) -> Set[Tuple[int, int]]:
        import random
        grid: List[List[Optional[str]]] = self.crossword.grid
        coords = [(r, c) for r in range(len(grid)) for c in range(len(grid[0])) if grid[r][c]]
        random.Random(seed).shuffle(coords)
        k = max(0, int(len(coords) * (percent / 100.0)))
        return set(coords[:k])

    # ---------- Internals ----------
    def _get_font(self, size: int, prefer: str = "arial") -> ImageFont.FreeTypeFont:
        key = (prefer, size)
        if key in self._font_cache:
            return self._font_cache[key]
        try:
            font = ImageFont.truetype(f"{prefer}.ttf", size=size)
        except Exception:
            font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    def _text_size(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        """Compatível com Pillow ≥10 (usa textbbox) e versões antigas (fallback)."""
        try:
            l, t, r, b = draw.textbbox((0, 0), text, font=font)
            return (r - l, b - t)
        except Exception:
            # fallbacks
            if hasattr(font, "getbbox"):
                l, t, r, b = font.getbbox(text)
                return (r - l, b - t)
            return (len(text) * max(6, getattr(font, "size", 12) // 2), getattr(font, "size", 12))

    def _draw_hatch_cell(
        self,
        base_img: Image.Image,
        rect: Tuple[int, int, int, int],
        *,
        color=(170, 170, 170, 255),
        spacing: int = 6,
        thickness: int = 1,
    ) -> None:
        """Hachura diagonal *apenas dentro* da célula (overlay com alpha)."""
        x0, y0, x1, y1 = rect
        w, h = max(1, x1 - x0), max(1, y1 - y0)

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        # Diagonal \\
        for i in range(-h, w, spacing):
            d.line([(i, 0), (i + h, h)], fill=color, width=thickness)
        # Diagonal / (mais clara)
        color2 = (color[0], color[1], color[2], max(80, color[3] // 2))
        for i in range(0, w + h, spacing):
            d.line([(i, 0), (0, i)], fill=color2, width=thickness)

        base_img.alpha_composite(overlay, dest=(x0, y0))
