from __future__ import annotations
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont


class WordSearchRenderer:
    """
    Renderizador de caça-palavras:
      - Exercício: grade + letras
      - Respostas: destaques (fill) OU linhas (stroke) nas palavras colocadas
    """

    BACKGROUND = (255, 255, 255)
    GRID = (30, 30, 30)
    TEXT = (0, 0, 0)
    HIGHLIGHT_FILL = (220, 240, 255)   # azul claro
    HIGHLIGHT_STROKE = (200, 0, 0)     # vermelho padrão

    def __init__(
        self,
        wordsearch,                 # instância de WordSearch
        *,
        cell_size: int = 40,
        padding: int = 25,
        highlight_style: str = "fill",   # "fill" ou "stroke"
        stroke_width: int = 5,
        font_path: str | None = None
    ) -> None:
        self.ws = wordsearch
        self.n = int(wordsearch.size)
        self.cell = int(cell_size)
        self.pad = int(padding)
        self.style = str(highlight_style or "fill").lower()
        self.stroke_width = int(stroke_width)
        self.font_path = font_path

        # fonte monoespaçada; fallback para default do PIL
        self.font = None
        if self.font_path:
            try:
                self.font = ImageFont.truetype(self.font_path, size=int(self.cell * 0.7))
            except Exception:
                self.font = None
        if self.font is None:
            try:
                self.font = ImageFont.truetype("DejaVuSansMono.ttf", size=int(self.cell * 0.7))
            except Exception:
                self.font = ImageFont.load_default()

    # ---------- API ----------

    def generate_image(self, filename: str, answers: bool = False) -> None:
        W = H = self.pad * 2 + self.n * self.cell
        img = Image.new("RGB", (W, H), self.BACKGROUND)
        draw = ImageDraw.Draw(img)

        self._draw_grid(draw)

        # Se for gabarito com FILL, desenhe os destaques ANTES das letras (para não cobri-las)
        if answers and self.style == "fill":
            self._draw_answers_fill(draw)

        self._draw_letters(draw)

        # Se for gabarito com STROKE, desenhe as linhas por cima
        if answers and self.style != "fill":
            self._draw_answers_stroke(draw)

        img.save(filename, format="PNG")

    # ---------- desenho básico ----------

    def _draw_grid(self, draw: ImageDraw.ImageDraw) -> None:
        # borda externa
        x0 = self.pad
        y0 = self.pad
        x1 = self.pad + self.n * self.cell
        y1 = self.pad + self.n * self.cell
        draw.rectangle([x0, y0, x1, y1], outline=self.GRID, width=1)

        # linhas/colunas
        for i in range(1, self.n):
            # horizontais
            y = self.pad + i * self.cell
            draw.line([self.pad, y, self.pad + self.n * self.cell, y], fill=self.GRID, width=1)
            # verticais
            x = self.pad + i * self.cell
            draw.line([x, self.pad, x, self.pad + self.n * self.cell], fill=self.GRID, width=1)

    def _draw_letters(self, draw: ImageDraw.ImageDraw) -> None:
        """
        Pillow 11 removeu `draw.textsize`. Use `font.getbbox` (ou `draw.textbbox` como fallback)
        e centralize compensando o offset do bbox (x0,y0) do glifo.
        """
        for r in range(self.n):
            for c in range(self.n):
                ch = self.ws.grid[r][c]
                if not ch:
                    continue
                cx = self.pad + c * self.cell + self.cell / 2
                cy = self.pad + r * self.cell + self.cell / 2

                # mede o glifo
                try:
                    # preferir getbbox pela estabilidade
                    bx0, by0, bx1, by1 = self.font.getbbox(ch)
                except Exception:
                    # fallback: usa o draw.textbbox
                    bx0, by0, bx1, by1 = draw.textbbox((0, 0), ch, font=self.font)

                w = bx1 - bx0
                h = by1 - by0
                # compensar o offset de origem do bbox (bx0,by0)
                x = cx - w / 2 - bx0
                y = cy - h / 2 - by0
                draw.text((x, y), ch, fill=self.TEXT, font=self.font)

    # ---------- gabarito ----------

    def _collect_placements(self) -> List[Tuple[str, int, int, int, int, int]]:
        placements = []
        for w, pos in (self.ws.placed_words or {}).items():
            r, c, dr, dc = pos["r"], pos["c"], pos["dr"], pos["dc"]
            L = len(w)
            placements.append((w, r, c, dr, dc, L))
        return placements

    def _draw_answers_fill(self, draw: ImageDraw.ImageDraw) -> None:
        cells: list[tuple[int, int]] = []
        for _, r, c, dr, dc, L in self._collect_placements():
            rr, cc = r, c
            for _ in range(L):
                cells.append((rr, cc))
                rr += dr
                cc += dc
        for rr, cc in cells:
            x0 = self.pad + cc * self.cell
            y0 = self.pad + rr * self.cell
            x1 = x0 + self.cell
            y1 = y0 + self.cell
            draw.rectangle([x0, y0, x1, y1], fill=self.HIGHLIGHT_FILL)

    def _draw_answers_stroke(self, draw: ImageDraw.ImageDraw) -> None:
        for _, r, c, dr, dc, L in self._collect_placements():
            x0 = self.pad + (c + 0.5) * self.cell
            y0 = self.pad + (r + 0.5) * self.cell
            x1 = self.pad + (c + (L - 1) * dc + 0.5) * self.cell
            y1 = self.pad + (r + (L - 1) * dr + 0.5) * self.cell
            draw.line([x0, y0, x1, y1], fill=self.HIGHLIGHT_STROKE, width=self.stroke_width)
