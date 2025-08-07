# src/engligen/rendering/image_renderer.py

from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List
import os

from engligen.core.crossword import Crossword
from engligen.rendering.clue_generator import ClueGenerator

class ImageRenderer:
    def __init__(self, crossword_obj: Crossword, clue_gen_obj: ClueGenerator, cell_size: int = 40, padding: int = 20):
        self.crossword = crossword_obj
        self.clue_generator = clue_gen_obj 
        self.cell_size = cell_size  # Padrão mantido, mas pode ser customizado
        self.padding = padding

        self.grid_width = self.crossword.width * self.cell_size
        self.grid_height = self.crossword.height * self.cell_size
        self.image_width = self.grid_width + self.padding * 2
        self.image_height = self.grid_height + self.padding * 2

        self.BG_COLOR = "white"
        self.BLACK = "black"
        self.TEXT_COLOR = "black"

        # Criar imagem com maior DPI para melhor qualidade
        self.image = Image.new("RGB", (self.image_width, self.image_height), self.BG_COLOR)
        self.draw = ImageDraw.Draw(self.image)

        try:
            # Fontes maiores para melhor legibilidade
            self.letter_font = ImageFont.truetype("arial.ttf", size=int(self.cell_size * 0.5))
            self.number_font = ImageFont.truetype("arialbd.ttf", size=int(self.cell_size * 0.25))
        except IOError:
            print("Fontes Arial não encontradas. Usando fontes padrão.")
            self.letter_font = ImageFont.load_default()
            self.number_font = ImageFont.load_default()

    def _is_clue_starting_cell(self, r: int, c: int) -> bool:
        """Verifica se a célula é onde uma dica começa (não deve ter letra)."""
        return (r, c) in self.clue_generator.clue_positions

    def _draw_grid_and_answers(self, include_answers: bool):
        """Desenha a grade e as respostas (se for o gabarito)."""
        for r in range(self.crossword.height):
            for c in range(self.crossword.width):
                x1, y1 = self.padding + c * self.cell_size, self.padding + r * self.cell_size
                
                if self.crossword.grid[r][c] is not None:
                    # Célula com letra - sempre desenha o quadrado branco
                    self.draw.rectangle(
                        [(x1, y1), (x1 + self.cell_size, y1 + self.cell_size)], 
                        fill=self.BG_COLOR, 
                        outline=self.BLACK, 
                        width=2  # Linha mais grossa para melhor definição
                    )
                    
                    # REGRA: Se é célula de início de dica, NÃO desenha letra
                    if include_answers and not self._is_clue_starting_cell(r, c):
                        letter = self.crossword.grid[r][c]
                        # Desenha a letra no centro da célula
                        self.draw.text(
                            (x1 + self.cell_size/2, y1 + self.cell_size/2), 
                            letter, 
                            font=self.letter_font, 
                            fill=self.TEXT_COLOR, 
                            anchor="mm"
                        )
                else:
                    # Célula vazia - pinta de preto
                    self.draw.rectangle(
                        [(x1, y1), (x1 + self.cell_size, y1 + self.cell_size)], 
                        fill=self.BLACK
                    )

    def _draw_clues(self):
        """Desenha os números das dicas e as setas nas células onde começam as palavras."""
        for (r, c), clues in self.clue_generator.clue_positions.items():
            x1, y1 = self.padding + c * self.cell_size, self.padding + r * self.cell_size
            
            if len(clues) >= 2:
                # Múltiplas dicas na mesma célula - desenha diagonal mais visível
                self.draw.line(
                    [(x1 + 5, y1 + 5), (x1 + self.cell_size - 5, y1 + self.cell_size - 5)], 
                    fill=self.BLACK, 
                    width=2  # Linha mais grossa
                )
                
                # Organiza as dicas por direção com melhor espaçamento
                horizontal_clues = []
                vertical_clues = []
                
                for clue in clues:
                    if 'horizontal' in clue['dir']:
                        horizontal_clues.append(clue)
                    else:
                        vertical_clues.append(clue)
                
                # Posiciona números nos triângulos com mais espaço
                for clue in horizontal_clues:
                    # Triângulo superior direito
                    pos = (x1 + self.cell_size * 0.75, y1 + self.cell_size * 0.25)
                    self.draw.text(
                        pos, 
                        clue['num'], 
                        font=self.number_font, 
                        anchor="mm", 
                        fill=self.TEXT_COLOR
                    )
                    # Seta no canto superior direito
                    self._draw_coquetel_arrow(r, c, clue['dir'], "top_right")
                
                for clue in vertical_clues:
                    # Triângulo inferior esquerdo
                    pos = (x1 + self.cell_size * 0.25, y1 + self.cell_size * 0.75)
                    self.draw.text(
                        pos, 
                        clue['num'], 
                        font=self.number_font, 
                        anchor="mm", 
                        fill=self.TEXT_COLOR
                    )
                    # Seta no canto inferior esquerdo
                    self._draw_coquetel_arrow(r, c, clue['dir'], "bottom_left")
            
            elif len(clues) == 1:
                # Uma única dica - número centralizado
                clue = clues[0]
                self.draw.text(
                    (x1 + self.cell_size * 0.5, y1 + self.cell_size * 0.5), 
                    clue['num'], 
                    font=self.number_font, 
                    anchor="mm", 
                    fill=self.TEXT_COLOR
                )
                # Seta pequena no canto apropriado baseada na direção
                corner = self._get_arrow_corner_for_single_clue(clue['dir'])
                self._draw_coquetel_arrow(r, c, clue['dir'], corner)

    def _get_arrow_corner_for_single_clue(self, direction: str) -> str:
        """Determina o canto onde a seta deve ficar para dicas únicas."""
        if direction == 'horizontal':
            return "top_right"
        elif direction == 'vertical':
            return "bottom_left"
        elif direction == 'horizontal_rev':
            return "top_left"
        elif direction == 'vertical_rev':
            return "bottom_right"
        else:
            return "top_right"  # padrão

    def _draw_coquetel_arrow(self, r: int, c: int, direction: str, corner_position: str):
        """Desenha setas pequenas e sutis no estilo Coquetel com posicionamento correto."""
        x1, y1 = self.padding + c * self.cell_size, self.padding + r * self.cell_size
        
        # Tamanho da seta maior para melhor visibilidade
        arrow_size = self.cell_size * 0.08
        
        # Posições dos cantos baseadas no parâmetro corner_position
        corner_positions = {
            "top_left": (x1 + self.cell_size * 0.15, y1 + self.cell_size * 0.15),
            "top_right": (x1 + self.cell_size * 0.85, y1 + self.cell_size * 0.15),
            "bottom_left": (x1 + self.cell_size * 0.15, y1 + self.cell_size * 0.85),
            "bottom_right": (x1 + self.cell_size * 0.85, y1 + self.cell_size * 0.85)
        }
        
        arrow_x, arrow_y = corner_positions[corner_position]
        
        # Desenha setas baseadas na direção REAL da palavra
        if direction == 'horizontal':  # →
            points = [
                (arrow_x + arrow_size, arrow_y),
                (arrow_x - arrow_size, arrow_y - arrow_size * 0.6),
                (arrow_x - arrow_size, arrow_y + arrow_size * 0.6)
            ]
            
        elif direction == 'vertical':  # ↓
            points = [
                (arrow_x, arrow_y + arrow_size),
                (arrow_x - arrow_size * 0.6, arrow_y - arrow_size),
                (arrow_x + arrow_size * 0.6, arrow_y - arrow_size)
            ]
            
        elif direction == 'horizontal_rev':  # ←
            points = [
                (arrow_x - arrow_size, arrow_y),
                (arrow_x + arrow_size, arrow_y - arrow_size * 0.6),
                (arrow_x + arrow_size, arrow_y + arrow_size * 0.6)
            ]
            
        elif direction == 'vertical_rev':  # ↑
            points = [
                (arrow_x, arrow_y - arrow_size),
                (arrow_x - arrow_size * 0.6, arrow_y + arrow_size),
                (arrow_x + arrow_size * 0.6, arrow_y + arrow_size)
            ]
        
        # Desenha a seta preenchida com contorno para melhor visibilidade
        self.draw.polygon(points, fill=self.BLACK, outline=self.BLACK)

    def generate_image(self, filename: str, include_answers: bool = False, dpi: int = 300):
        """Orquestra o processo de desenho e salva a imagem final com alta qualidade."""
        # A geração de dicas de texto precisa acontecer antes para popular os dados
        self.clue_generator.generate_text_file(filename.replace(".png", "_clues.txt"))
        
        self._draw_grid_and_answers(include_answers)
        if not include_answers:
            self._draw_clues()

        output_dir = "output"
        if not os.path.exists(output_dir): 
            os.makedirs(output_dir)
        filepath = os.path.join(output_dir, filename)
        
        # Salva com maior qualidade
        self.image.save(filepath, dpi=(dpi, dpi), optimize=True)
        print(f"Imagem '{filepath}' gerada com sucesso em {dpi} DPI!")