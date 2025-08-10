import random
import string
from typing import List, Optional, Tuple, Dict

class WordSearch:
    """
    Gera uma grelha de caça-palavras a partir de uma lista de palavras.
    """
    def __init__(self, words: List[str], size: int = 15):
        self.words = sorted([word.upper() for word in words if len(word) <= size], key=len, reverse=True)
        self.size = size
        self.width = size
        self.height = size
        self.grid: List[List[str]] = [['' for _ in range(size)] for _ in range(size)]
        self.placed_words: Dict[str, str] = {}

    def generate(self) -> bool:
        """Tenta posicionar todas as palavras na grelha."""
        directions = [
            (0, 1), (1, 0), (1, 1),
            (0, -1), (-1, 0), (-1, -1),
            (1, -1), (-1, 1)
        ]
        
        for word in self.words:
            random.shuffle(directions)
            for dr, dc in directions:
                if self._try_place_word(word, dr, dc):
                    self.placed_words[word] = self._get_direction_name(dr, dc)
                    break
        
        self._fill_empty_cells()
        return len(self.placed_words) > 0

    def _try_place_word(self, word: str, dr: int, dc: int) -> bool:
        """Tenta encontrar um local para a palavra numa direção específica."""
        len_word = len(word)
        possible_starts = []
        for r in range(self.size):
            for c in range(self.size):
                if self._can_place_here(word, r, c, dr, dc):
                    possible_starts.append((r, c))
        
        if not possible_starts:
            return False
            
        r_start, c_start = random.choice(possible_starts)
        for i, char in enumerate(word):
            self.grid[r_start + i * dr][c_start + i * dc] = char
        return True

    def _can_place_here(self, word: str, r: int, c: int, dr: int, dc: int) -> bool:
        """Verifica se uma palavra pode ser colocada numa posição e direção."""
        len_word = len(word)
        if not (0 <= r + (len_word - 1) * dr < self.size and 0 <= c + (len_word - 1) * dc < self.size):
            return False
        
        for i, char in enumerate(word):
            cell = self.grid[r + i * dr][c + i * dc]
            if cell != '' and cell != char:
                return False
        return True

    def _fill_empty_cells(self):
        """Preenche as células vazias da grelha com letras aleatórias."""
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == '':
                    self.grid[r][c] = random.choice(string.ascii_uppercase)

    def _get_direction_name(self, dr: int, dc: int) -> str:
        """Retorna o nome da direção com base nos deltas."""
        if dr == 0 and dc == 1: return "→"
        if dr == 0 and dc == -1: return "←"
        if dr == 1 and dc == 0: return "↓"
        if dr == -1 and dc == 0: return "↑"
        if dr == 1 and dc == 1: return "↘"
        if dr == -1 and dc == -1: return "↖"
        if dr == 1 and dc == -1: return "↙"
        if dr == -1 and dc == 1: return "↗"
        return "?"