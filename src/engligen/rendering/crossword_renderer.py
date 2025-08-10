
from PIL import Image, ImageDraw, ImageFont
import os

class CrosswordRenderer:
    """
    Renderiza uma grade de palavras-cruzadas com numeração e indicadores de direção.

    Parâmetros
    ----------
    crossword_obj : objeto com atributos `width`, `height` e `grid`
    clue_gen_obj  : objeto com `clue_positions[(r, c)] -> List[{"num": str, "dir": "horizontal"|"vertical"}]`
    cell_size     : int, tamanho do lado de cada célula em pixels
    padding       : int, margem externa em pixels
    corner_pad    : int, padding dentro da célula para itens nos cantos (default=2)
    arrow_gap_factor : float, fração do `cell_size` usada como folga entre número e seta ↓ (default=0.08)
    arrow_gap_px  : int|None, folga fixa em pixels (se definido, tem prioridade sobre `arrow_gap_factor`)

    Observação
    ----------
    - Número fica no canto superior-esquerdo.
    - Seta → no canto superior-direito.
    - Seta ↓ posicionada logo abaixo do número (com fallback automático para o canto inferior-esquerdo se não couber).
    """
    def __init__(self, crossword_obj, clue_gen_obj, cell_size=40, padding=25,
                 corner_pad=2, arrow_gap_factor=0.08, arrow_gap_px=None):
        self.crossword = crossword_obj
        self.clues = clue_gen_obj
        self.cell_size = cell_size
        self.padding = padding
        self.corner_pad = int(corner_pad)
        self.arrow_gap_factor = float(arrow_gap_factor)
        self.arrow_gap_px = None if arrow_gap_px is None else int(arrow_gap_px)

        # Cores
        self.BACKGROUND_COLOR = (255, 255, 255)
        self.CELL_COLOR = (255, 255, 255)
        self.BLOCK_COLOR = (0, 0, 0)
        self.LINE_COLOR = (0, 0, 0)
        self.TEXT_COLOR = (0, 0, 0)

        # Dimensões da imagem
        self.grid_width = self.crossword.width * self.cell_size
        self.grid_height = self.crossword.height * self.cell_size
        self.image_width = self.grid_width + 2 * self.padding
        self.image_height = self.grid_height + 2 * self.padding

        # Carrega as fontes
        try:
            self.font = ImageFont.truetype("arial.ttf", size=int(self.cell_size * 0.6))
            self.small_font = ImageFont.truetype("arial.ttf", size=int(self.cell_size * 0.25))
        except IOError:
            self.font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()

    def generate_image(self, filename: str, answers: bool = False, dpi: int = 300, is_wordsearch: bool = False):
        """Cria e salva a imagem do exercício."""
        image = Image.new("RGB", (self.image_width, self.image_height), self.BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)

        self._draw_grid(draw)
        if answers:
            self._draw_answers(draw)

        # Garante que a pasta de saída existe
        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        image.save(filename, dpi=(dpi, dpi))
        print(f"🖼️  Imagem '{os.path.basename(filename)}' gerada com sucesso!")

    def _draw_grid(self, draw):
        """Desenha a grade, blocos e metainformações (número e setas)."""
        for r in range(self.crossword.height):
            for c in range(self.crossword.width):
                x0 = self.padding + c * self.cell_size
                y0 = self.padding + r * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size

                if self.crossword.grid[r][c] is None:
                    draw.rectangle([x0, y0, x1, y1], fill=self.BLOCK_COLOR)
                    continue

                draw.rectangle([x0, y0, x1, y1], fill=self.CELL_COLOR, outline=self.LINE_COLOR)

                # Informações de dica que começam nesta célula (se houver)
                clue_info_list = self.clues.clue_positions.get((r, c))
                if not clue_info_list:
                    continue

                # Número da dica (compartilhado entre as direções que iniciam nesta célula)
                number_text = clue_info_list[0]['num']

                # Bounding box do número (para medidas robustas)
                nb = draw.textbbox((0, 0), number_text, font=self.small_font)
                n_h = nb[3] - nb[1]

                pad = self.corner_pad

                # 1) Número no canto superior-esquerdo
                num_x = x0 + pad
                num_y = y0 + pad
                draw.text((num_x, num_y), number_text, fill=self.TEXT_COLOR, font=self.small_font)

                has_horizontal = any(info['dir'] == 'horizontal' for info in clue_info_list)
                has_vertical   = any(info['dir'] == 'vertical'   for info in clue_info_list)

                # 2) Seta → (Across) no canto superior-direito
                if has_horizontal:
                    right_arrow = '→'
                    rb = draw.textbbox((0, 0), right_arrow, font=self.small_font)
                    r_w = rb[2] - rb[0]
                    draw.text((x1 - pad - r_w, y0 + pad), right_arrow, fill=self.TEXT_COLOR, font=self.small_font)

                # 3) Seta ↓ (Down) logo abaixo do número (fallback pro canto inferior-esquerdo)
                if has_vertical:
                    down_arrow = '↓'
                    db = draw.textbbox((0, 0), down_arrow, font=self.small_font)
                    d_h = db[3] - db[1]

                    # Folga entre número e seta: px fixo OU fração do cell_size
                    if self.arrow_gap_px is not None:
                        gap = max(1, self.arrow_gap_px)
                    else:
                        gap = max(1, int(self.cell_size * self.arrow_gap_factor))

                    y_down = num_y + n_h + gap  # logo abaixo do número
                    if y_down + d_h > y1 - pad:
                        # Se não couber, posiciona no canto inferior-esquerdo
                        y_down = y1 - pad - d_h

                    draw.text((x0 + pad, y_down), down_arrow, fill=self.TEXT_COLOR, font=self.small_font)

    def _draw_answers(self, draw):
        """Desenha as letras das respostas na grade."""
        for r in range(self.crossword.height):
            for c in range(self.crossword.width):
                letter = self.crossword.grid[r][c]
                if not letter:
                    continue

                x = self.padding + c * self.cell_size
                y = self.padding + r * self.cell_size

                text_bbox = draw.textbbox((0,0), letter, font=self.font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                text_x = x + (self.cell_size - text_width) / 2
                text_y = y + (self.cell_size - text_height) / 2

                draw.text((text_x, text_y), letter, fill=self.TEXT_COLOR, font=self.font)
