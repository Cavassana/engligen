
import random
import string
from typing import List, Optional, Tuple, Dict, Any

class WordSearch:
    """
    Gera uma grelha de caça-palavras a partir de uma lista de palavras.
    Mantém, para cada palavra colocada, as coordenadas de início e a direção.
    """
    def __init__(self, words: List[str], size: int = 15):
        self.words = sorted([w.upper() for w in words if w and len(w) <= size], key=len, reverse=True)
        self.size = size
        self.width = size
        self.height = size
        self.grid: List[List[str]] = [['' for _ in range(size)] for _ in range(size)]
        # word -> {'r': int, 'c': int, 'dr': int, 'dc': int, 'arrow': str}
        self.placed_words: Dict[str, Dict[str, Any]] = {}

    def generate(self) -> bool:
        """Tenta posicionar todas as palavras na grelha."""
        directions: List[Tuple[int,int]] = [
            (0, 1), (1, 0), (1, 1),
            (0, -1), (-1, 0), (-1, -1),
            (1, -1), (-1, 1)
        ]

        for word in self.words:
            random.shuffle(directions)
            placed = False
            for dr, dc in directions:
                result = self._try_place_word(word, dr, dc)
                if result is not None:
                    r0, c0 = result
                    self.placed_words[word] = {
                        'r': r0, 'c': c0, 'dr': dr, 'dc': dc,
                        'arrow': self._get_direction_name(dr, dc)
                    }
                    placed = True
                    break
            # Se não coube, apenas ignore (pode acontecer com grids pequenas)
        self._fill_empty_cells()
        return len(self.placed_words) > 0

    def _try_place_word(self, word: str, dr: int, dc: int) -> Optional[Tuple[int,int]]:
        """Tenta encontrar e ocupar um local para a palavra numa direção específica.
        Retorna (r_start, c_start) em caso de sucesso; do contrário, None.
        """
        len_word = len(word)
        possible_starts: List[Tuple[int,int]] = []
        for r in range(self.size):
            for c in range(self.size):
                if self._can_place_here(word, r, c, dr, dc):
                    possible_starts.append((r, c))

        if not possible_starts:
            return None

        r_start, c_start = random.choice(possible_starts)
        for i, ch in enumerate(word):
            self.grid[r_start + i * dr][c_start + i * dc] = ch
        return (r_start, c_start)

    def _can_place_here(self, word: str, r: int, c: int, dr: int, dc: int) -> bool:
        """Verifica se uma palavra pode ser colocada numa posição e direção."""
        len_word = len(word)
        end_r = r + (len_word - 1) * dr
        end_c = c + (len_word - 1) * dc
        if not (0 <= end_r < self.size and 0 <= end_c < self.size):
            return False
        for i, ch in enumerate(word):
            rr = r + i * dr
            cc = c + i * dc
            cell = self.grid[rr][cc]
            if cell != '' and cell != ch:
                return False
        return True

    def _fill_empty_cells(self) -> None:
        """Preenche as células vazias da grelha com letras aleatórias."""
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == '':
                    self.grid[r][c] = random.choice(string.ascii_uppercase)

    def _get_direction_name(self, dr: int, dc: int) -> str:
        """Retorna o símbolo da direção com base nos deltas."""
        if dr == 0 and dc == 1: return "→"
        if dr == 0 and dc == -1: return "←"
        if dr == 1 and dc == 0: return "↓"
        if dr == -1 and dc == 0: return "↑"
        if dr == 1 and dc == 1: return "↘"
        if dr == -1 and dc == -1: return "↖"
        if dr == 1 and dc == -1: return "↙"
        if dr == -1 and dc == 1: return "↗"
        return "?"
