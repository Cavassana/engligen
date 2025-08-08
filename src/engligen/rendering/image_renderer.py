from PIL import Image, ImageDraw, ImageFont
import os
from typing import List, Dict

from engligen.core.crossword import Crossword
from engligen.rendering.clue_generator import ClueGenerator

class ImageRenderer:
    """
    Renderiza a grade de palavras cruzadas, incluindo números e indicadores
    de direção de forma clara e bem posicionada.
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
        
        # Dimensões da imagem
        self.grid_width = self.crossword.width * self.cell_size
        self.grid_height = self.crossword.height * self.cell_size
        self.image_width = self.grid_width + 2 * self.padding
        self.image_height = self.grid_height + 2 * self.padding

        # Inicializa a imagem
        self.image = Image.new("RGB", (self.image_width, self.image_height), self.BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)

        # Carrega as fontes
        try:
            self.letter_font = ImageFont.truetype("arial.ttf", int(self.cell_size * 0.6))
            self.number_font = ImageFont.truetype("arialbd.ttf", int(self.cell_size * 0.28))
            # Fonte menor para os indicadores de direção
            self.indicator_font = ImageFont.truetype("arial.ttf", int(self.cell_size * 0.25))
        except IOError:
            print("⚠️  Aviso: Fontes Arial não encontradas. Usando fontes padrão.")
            self.letter_font = ImageFont.load_default()
            self.number_font = ImageFont.load_default()
            self.indicator_font = ImageFont.load_default()

    def _draw_grid_and_answers(self, include_answers: bool):
        """Desenha a grade e as letras (se for o gabarito)."""
        for r in range(self.crossword.height):
            for c in range(self.crossword.width):
                x1 = self.padding + c * self.cell_size
                y1 = self.padding + r * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                if self.crossword.grid[r][c] is None:
                    # Células não usadas podem ser preenchidas ou deixadas em branco.
                    # Preencher de preto é o estilo clássico.
                    self.draw.rectangle([x1, y1, x2, y2], fill=self.BLACK)
                else:
                    self.draw.rectangle([x1, y1, x2, y2], outline=self.BLACK, fill=self.BG_COLOR)
                    if include_answers:
                        letter = self.crossword.grid[r][c]
                        self.draw.text(
                            (x1 + self.cell_size / 2, y1 + self.cell_size / 2),
                            letter, font=self.letter_font, fill=self.TEXT_COLOR, anchor="mm"
                        )

    def _draw_clues_and_indicators(self):
        """
        NOVA LÓGICA: Desenha os números das dicas e os indicadores de direção (→, ↓)
        de forma inteligente dentro da célula.
        """
        # Margem interna para o posicionamento dos elementos
        cell_padding = self.cell_size * 0.1

        for (r, c), clues in self.clue_generator.clue_positions.items():
            num = clues[0]['num']
            
            # Posição base para o número no canto superior esquerdo
            x_base = self.padding + c * self.cell_size + cell_padding
            y_base = self.padding + r * self.cell_size + cell_padding
            
            # Desenha o número da dica
            self.draw.text((x_base, y_base), num, font=self.number_font, fill=self.BLACK, anchor="lt")
            
            # Pega a bounding box do número para posicionar os indicadores ao lado
            try: # O método textbbox é mais preciso
                num_bbox = self.draw.textbbox((x_base, y_base), num, font=self.number_font, anchor="lt")
                indicator_x_start = num_bbox[2] + self.cell_size * 0.05 # Posição X após o número
            except AttributeError: # Fallback para versões mais antigas da Pillow
                indicator_x_start = x_base + self.cell_size * 0.2 # Posição X estimada

            indicator_y_start = y_base + self.cell_size * 0.02

            # Desenha os indicadores para cada direção originada nesta célula
            for clue_info in clues:
                direction = clue_info.get('dir')
                indicator = ''
                if direction == 'horizontal':
                    indicator = '→'
                elif direction == 'vertical':
                    indicator = '↓'
                
                if indicator:
                    self.draw.text((indicator_x_start, indicator_y_start), indicator, font=self.indicator_font, fill=self.BLACK, anchor="lt")
                    # Move a posição X para o próximo indicador, caso haja mais de um
                    indicator_x_start += self.cell_size * 0.2


    def generate_image(self, filename: str, answers: bool = False, dpi: int = 300):
        """Orquestra o desenho e salva a imagem final."""
        filepath = os.path.join("output", filename)
        os.makedirs("output", exist_ok=True)
        
        self._draw_grid_and_answers(answers)
        
        # Só desenha os números e indicadores na folha de exercício
        if not answers:
            self._draw_clues_and_indicators()
            
        self.image.save(filepath, dpi=(dpi, dpi), optimize=True)
        print(f"🖼️  Imagem '{filename}' gerada com sucesso!")