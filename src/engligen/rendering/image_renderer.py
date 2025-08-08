from PIL import Image, ImageDraw, ImageFont
import os
from typing import List, Dict

from engligen.core.crossword import Crossword
from engligen.rendering.clue_generator import ClueGenerator

class ImageRenderer:
    """
    Renderiza a grade de palavras cruzadas, incluindo números e setas
    para indicar a direção das palavras (estilo "Coquetel").
    """
    def __init__(
        self,
        crossword_obj: Crossword,
        clue_gen_obj: ClueGenerator,
        cell_size: int = 40,
        padding: int = 25,
    ):
        self.crossword = crossword_obj
        self.clue_generator = clue_gen_obj
        self.cell_size = cell_size
        self.padding = padding

        # Cores
        self.BG_COLOR = "white"
        self.BLACK = (0, 0, 0)
        self.TEXT_COLOR = (0, 0, 0)
        
        # Calcula dimensões da imagem
        self.grid_width = self.crossword.width * self.cell_size
        self.grid_height = self.crossword.height * self.cell_size
        self.image_width = self.grid_width + 2 * self.padding
        self.image_height = self.grid_height + 2 * self.padding

        # Inicializa a imagem e o objeto de desenho
        self.image = Image.new("RGB", (self.image_width, self.image_height), self.BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)

        # Carrega as fontes
        try:
            self.letter_font = ImageFont.truetype("arial.ttf", int(self.cell_size * 0.6))
            self.number_font = ImageFont.truetype("arialbd.ttf", int(self.cell_size * 0.28))
        except IOError:
            print("Fontes Arial não encontradas. Usando fontes padrão.")
            self.letter_font = ImageFont.load_default()
            self.number_font = ImageFont.load_default()

    def _draw_grid_and_answers(self, include_answers: bool):
        """Desenha a grade e as letras (se for o gabarito)."""
        for r in range(self.crossword.height):
            for c in range(self.crossword.width):
                x1 = self.padding + c * self.cell_size
                y1 = self.padding + r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                if self.crossword.grid[r][c] is None:
                    self.draw.rectangle([x1, y1, x2, y2], fill=self.BLACK)
                else:
                    self.draw.rectangle([x1, y1, x2, y2], outline=self.BLACK, fill=self.BG_COLOR)
                    if include_answers:
                        letter = self.crossword.grid[r][c]
                        self.draw.text(
                            (x1 + self.cell_size / 2, y1 + self.cell_size / 2),
                            letter, font=self.letter_font, fill=self.TEXT_COLOR, anchor="mm"
                        )

    def _get_arrow_corner_for_single_clue(self, direction: str) -> tuple:
        """Determina o canto para a seta de uma única dica na célula."""
        if direction == "horizontal": return ("top_left", "top_right")
        if direction == "vertical": return ("top_left", "bottom_left")
        if direction == "horizontal_rev": return ("bottom_right", "bottom_left")
        if direction == "vertical_rev": return ("bottom_right", "top_right")
        return ()

    def _draw_coquetel_arrow(self, r: int, c: int, corner_position: str):
        """Desenha uma seta pequena no canto da célula."""
        arrow_size = self.cell_size * 0.18
        x1, y1, _, _ = (self.padding + c * self.cell_size, self.padding + r * self.cell_size, 0, 0)

        if corner_position == "top_left":
            points = [(x1, y1), (x1 + arrow_size, y1), (x1, y1 + arrow_size)]
        elif corner_position == "top_right":
            points = [(x1 + self.cell_size, y1), (x1 + self.cell_size - arrow_size, y1), (x1 + self.cell_size, y1 + arrow_size)]
        elif corner_position == "bottom_left":
            points = [(x1, y1 + self.cell_size), (x1, y1 + self.cell_size - arrow_size), (x1 + arrow_size, y1 + self.cell_size)]
        elif corner_position == "bottom_right":
            points = [(x1 + self.cell_size, y1 + self.cell_size), (x1 + self.cell_size, y1 + self.cell_size - arrow_size), (x1 + self.cell_size - arrow_size, y1 + self.cell_size)]
        else:
            return
            
        self.draw.polygon(points, fill=self.BLACK)

    def _draw_clues(self):
        """Desenha os números das dicas e as setas."""
        for (r, c), clues in self.clue_generator.clue_positions.items():
            num = clues[0]['num']
            x_pos = self.padding + c * self.cell_size + (self.cell_size * 0.12)
            y_pos = self.padding + r * self.cell_size + (self.cell_size * 0.08)
            self.draw.text((x_pos, y_pos), num, font=self.number_font, fill=self.BLACK)
            
            # Lógica para desenhar setas e/ou linhas diagonais
            if len(clues) == 1:
                corners = self._get_arrow_corner_for_single_clue(clues[0]['dir'])
                if corners:
                    self._draw_coquetel_arrow(r, c, corners[0])
                    self._draw_coquetel_arrow(r, c, corners[1])
            else: # Célula com dica horizontal e vertical
                x1 = self.padding + c * self.cell_size
                y1 = self.padding + r * self.cell_size
                self.draw.line([(x1, y1), (x1 + self.cell_size, y1 + self.cell_size)], fill=self.BLACK, width=1)

    def generate_image(self, filename: str, answers: bool = False, dpi: int = 300):
        """Orquestra o desenho e salva a imagem final."""
        filepath = os.path.join("output", filename)
        os.makedirs("output", exist_ok=True)
        
        self._draw_grid_and_answers(answers)
        if not answers:
            self._draw_clues()
            
        self.image.save(filepath, dpi=(dpi, dpi), optimize=True)
        print(f"Imagem '{filename}' gerada com sucesso em {dpi} DPI!")