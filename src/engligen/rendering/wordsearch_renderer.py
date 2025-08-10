from PIL import Image, ImageDraw, ImageFont
import os
from engligen.core.word_search import WordSearch
from typing import Dict

class WordSearchRenderer:
    """
    Renderiza uma grelha de caça-palavras para uma imagem.
    """
    def __init__(self, wordsearch_obj: WordSearch, cell_size: int = 30, padding: int = 25):
        self.wordsearch = wordsearch_obj
        self.cell_size = cell_size
        self.padding = padding

        # Cores
        self.BACKGROUND_COLOR = (255, 255, 255)
        self.CELL_COLOR = (255, 255, 255)
        self.LINE_COLOR = (0, 0, 0)
        self.TEXT_COLOR = (0, 0, 0)
        self.ANSWER_HIGHLIGHT_COLOR = (255, 255, 0) # Amarelo para destacar respostas

        # Dimensões
        self.grid_size = self.wordsearch.size * self.cell_size
        self.image_width = self.grid_size + 2 * self.padding
        self.image_height = self.grid_size + 2 * self.padding

        # Fontes
        try:
            self.font = ImageFont.truetype("arial.ttf", size=int(self.cell_size * 0.6))
        except IOError:
            self.font = ImageFont.load_default()

    def generate_image(self, filename: str, answers: bool = False, dpi: int = 300):
        """Cria e salva a imagem do caça-palavras."""
        image = Image.new("RGB", (self.image_width, self.image_height), self.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)

        if answers:
            self._draw_answers(draw) # Desenha as respostas primeiro para ficarem no fundo

        self._draw_grid(draw)

        # Garante que a pasta de saída existe
        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        image.save(filename, dpi=(dpi, dpi))
        print(f"🖼️  Imagem '{os.path.basename(filename)}' gerada com sucesso!")

    def _draw_grid(self, draw):
        """Desenha a grelha e as letras."""
        for r in range(self.wordsearch.size):
            for c in range(self.wordsearch.size):
                x0 = self.padding + c * self.cell_size
                y0 = self.padding + r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size

                # Desenha a célula
                draw.rectangle([x0, y0, x1, y1], outline=self.LINE_COLOR)

                # Desenha a letra
                letter = self.wordsearch.grid[r][c]
                text_bbox = draw.textbbox((0,0), letter, font=self.font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = x0 + (self.cell_size - text_width) / 2
                text_y = y0 + (self.cell_size - text_height) / 2
                draw.text((text_x, text_y), letter, fill=self.TEXT_COLOR, font=self.font)

    def _draw_answers(self, draw):
        """Destaca as palavras encontradas na grelha."""
        for word, info in self.wordsearch.placed_words.items():
            r, c = info['r'], info['c']
            dr, dc = info['dr'], info['dc']
            word_len = len(word)

            for i in range(word_len):
                cell_r, cell_c = r + i * dr, c + i * dc
                x0 = self.padding + cell_c * self.cell_size
                y0 = self.padding + cell_r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                draw.rectangle([x0, y0, x1, y1], fill=self.ANSWER_HIGHLIGHT_COLOR)