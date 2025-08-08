import random
from typing import List, Optional, Dict

class Crossword:
    """
    Gera uma grade de palavras-cruzadas com suporte para palavras em
    quatro direções: horizontal, vertical, e suas versões reversas.
    """
    def __init__(self, words: List[str], width: int = 30, height: int = 20):
        # Filtra palavras curtas e ordena da maior para a menor para otimizar o encaixe
        unique_words = sorted(list(set(w.upper() for w in words if len(w) > 2)), key=len, reverse=True)
        self.word_list = unique_words
        self.width = width
        self.height = height
        self.grid: List[List[Optional[str]]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        
        # Mantém metadados das palavras colocadas
        self.placed_words: Dict[str, Dict] = {}
        
        # Define as quatro direções e seus deltas (mudança em linha, mudança em coluna)
        self.directions = {
            "horizontal": (0, 1),
            "vertical": (1, 0),
            "horizontal_rev": (0, -1),
            "vertical_rev": (1, -1)
        }

    def generate(self) -> bool:
        if not self.word_list:
            return False

        # Tenta colocar a primeira palavra no centro
        first_word = self.word_list.pop(0)
        row = self.height // 2
        col = (self.width - len(first_word)) // 2
        if not self._place_word(first_word, row, col if col > 0 else 0, "horizontal"):
             # Se falhar, tenta colocar em outro lugar (lógica de fallback pode ser adicionada aqui)
             return False

        # Tenta encaixar as palavras restantes
        words_to_try = self.word_list[:]
        random.shuffle(words_to_try)

        for word in words_to_try:
            placements = self._find_best_placements_for(word)
            if placements:
                best = placements[0] # Usa o melhor encaixe (maior número de interseções)
                self._place_word(word, best["row"], best["col"], best["direction"])

        if self.placed_words:
            self._trim_grid() # Remove espaços vazios ao redor da grade final
            return True
        return False

    def _find_best_placements_for(self, word: str) -> List[Dict]:
        placements: List[Dict] = []
        for i, letter in enumerate(word):
            for r in range(self.height):
                for c in range(self.width):
                    if self.grid[r][c] == letter:
                        # Para cada direção, calcula a posição inicial e verifica se pode ser colocada
                        for d_name, (dr, dc) in self.directions.items():
                            row_start, col_start = r - i * dr, c - i * dc
                            if self._can_place_word_at(word, row_start, col_start, d_name):
                                intersections = self._count_intersections(word, row_start, col_start, d_name)
                                placements.append({"row": row_start, "col": col_start, "direction": d_name, "intersections": intersections})
        
        # Ordena para priorizar os encaixes com mais interseções
        placements.sort(key=lambda p: p["intersections"], reverse=True)
        return placements

    def _can_place_word_at(self, word: str, row: int, col: int, direction: str) -> bool:
        if word in self.placed_words:
            return False
        
        L = len(word)
        dr, dc = self.directions[direction]

        for i in range(L):
            r, c = row + i * dr, col + i * dc
            
            # Verifica se está dentro dos limites da grade
            if not (0 <= r < self.height and 0 <= c < self.width):
                return False
                
            # Verifica se a célula está vazia ou contém a letra correspondente
            if self.grid[r][c] not in (None, word[i]):
                return False
        return True

    def _count_intersections(self, word: str, row: int, col: int, direction: str) -> int:
        count = 0
        dr, dc = self.directions[direction]
        for i, char in enumerate(word):
            try:
                if self.grid[row + i * dr][col + i * dc] == char:
                    count += 1
            except IndexError:
                return 0
        return count

    def _place_word(self, word: str, row: int, col: int, direction: str) -> bool:
        if not self._can_place_word_at(word, row, col, direction):
            return False
            
        self.placed_words[word] = {"row": row, "col": col, "direction": direction}
        dr, dc = self.directions[direction]
        for i, char in enumerate(word):
            self.grid[row + i * dr][col + i * dc] = char
        return True

    def _trim_grid(self) -> None:
        if not self.placed_words:
            self.grid, self.width, self.height = [], 0, 0
            return

        min_r, max_r, min_c, max_c = self.height, -1, self.width, -1
        for word, info in self.placed_words.items():
            r, c, d, L = info["row"], info["col"], info["direction"], len(word)
            dr, dc = self.directions[d]
            
            min_r = min(min_r, r, r + (L - 1) * dr)
            max_r = max(max_r, r, r + (L - 1) * dr)
            min_c = min(min_c, c, c + (L - 1) * dc)
            max_c = max(max_c, c, c + (L - 1) * dc)
        
        # Adiciona uma pequena margem
        min_r = max(0, min_r - 1)
        min_c = max(0, min_c - 1)
        max_r = min(self.height - 1, max_r + 1)
        max_c = min(self.width - 1, max_c + 1)

        self.grid = [row[min_c:max_c + 1] for row in self.grid[min_r:max_r + 1]]

        # Atualiza as coordenadas das palavras colocadas
        new_placed_words: Dict[str, Dict] = {}
        for word, info in self.placed_words.items():
            new_placed_words[word] = {
                "row": info["row"] - min_r,
                "col": info["col"] - min_c,
                "direction": info["direction"],
            }
        self.placed_words = new_placed_words
        self.height = len(self.grid)
        self.width = len(self.grid[0]) if self.height > 0 else 0