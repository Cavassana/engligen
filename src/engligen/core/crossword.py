# src/engligen/core/crossword.py

from typing import List, Optional, Dict
import random

class Crossword:
    """
    Gera uma grade de palavras-cruzadas com suporte para palavras em
    quatro direções: horizontal, vertical, e suas versões reversas.
    """
    def __init__(self, words: List[str], width: int = 30, height: int = 20):
        unique_words = sorted(list(set(w.upper() for w in words if len(w) > 2)), key=len, reverse=True)
        self.word_list = unique_words
        self.width = width
        self.height = height
        self.grid: List[List[Optional[str]]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.placed_words: Dict[str, Dict] = {}
        self.directions = ['horizontal', 'vertical', 'horizontal_rev', 'vertical_rev']

    def generate(self) -> bool:
        if not self.word_list:
            return False

        first_word = self.word_list.pop(0)
        row = self.height // 2
        col = (self.width - len(first_word)) // 2
        if col < 0: col = 0 # Garante que a palavra caiba se for muito grande
            
        self._place_word(first_word, row, col, 'horizontal')

        words_to_try = self.word_list[:]
        random.shuffle(words_to_try)

        for word in words_to_try:
            placements = self._find_best_placements_for(word)
            if placements:
                best_placement = placements[0]
                self._place_word(word, best_placement['row'], best_placement['col'], best_placement['direction'])
        
        if self.placed_words:
            self._trim_grid()
            return True
        return False

    def _find_best_placements_for(self, word: str) -> List[Dict]:
        placements = []
        for i, letter in enumerate(word):
            for r in range(self.height):
                for c in range(self.width):
                    if self.grid[r][c] == letter:
                        for direction in self.directions:
                            if direction == 'horizontal':
                                col_start = c - i
                                if self._can_place_word_at(word, r, col_start, direction):
                                    intersections = self._count_intersections(word, r, col_start, direction)
                                    placements.append({'row': r, 'col': col_start, 'direction': direction, 'intersections': intersections})
                            elif direction == 'vertical':
                                row_start = r - i
                                if self._can_place_word_at(word, row_start, c, direction):
                                    intersections = self._count_intersections(word, row_start, c, direction)
                                    placements.append({'row': row_start, 'col': c, 'direction': direction, 'intersections': intersections})
                            elif direction == 'horizontal_rev':
                                col_start = c + i
                                if self._can_place_word_at(word, r, col_start, direction):
                                    intersections = self._count_intersections(word, r, col_start, direction)
                                    placements.append({'row': r, 'col': col_start, 'direction': direction, 'intersections': intersections})
                            elif direction == 'vertical_rev':
                                row_start = r + i
                                if self._can_place_word_at(word, row_start, c, direction):
                                    intersections = self._count_intersections(word, row_start, c, direction)
                                    placements.append({'row': row_start, 'col': c, 'direction': direction, 'intersections': intersections})

        placements.sort(key=lambda p: p['intersections'], reverse=True)
        return placements

    def _can_place_word_at(self, word: str, row: int, col: int, direction: str) -> bool:
        if word in self.placed_words:
            return False

        word_len = len(word)
        
        if direction == 'horizontal':
            if col < 0 or col + word_len > self.width: return False
            for i in range(word_len):
                if self.grid[row][col + i] is not None and self.grid[row][col + i] != word[i]: return False

        elif direction == 'vertical':
            if row < 0 or row + word_len > self.height: return False
            for i in range(word_len):
                if self.grid[row + i][col] is not None and self.grid[row + i][col] != word[i]: return False

        elif direction == 'horizontal_rev':
            if col >= self.width or col - word_len < -1: return False
            for i in range(word_len):
                if self.grid[row][col - i] is not None and self.grid[row][col - i] != word[i]: return False
        
        elif direction == 'vertical_rev':
            if row >= self.height or row - word_len < -1: return False
            for i in range(word_len):
                if self.grid[row - i][col] is not None and self.grid[row - i][col] != word[i]: return False

        return True

    def _count_intersections(self, word: str, row: int, col: int, direction: str) -> int:
        intersections = 0
        for i, letter in enumerate(word):
            try:
                if direction == 'horizontal':
                    if self.grid[row][col + i] == letter: intersections += 1
                elif direction == 'vertical':
                    if self.grid[row + i][col] == letter: intersections += 1
                elif direction == 'horizontal_rev':
                    if self.grid[row][col - i] == letter: intersections += 1
                elif direction == 'vertical_rev':
                    if self.grid[row - i][col] == letter: intersections += 1
            except IndexError:
                return 0
        return intersections

    def _place_word(self, word: str, row: int, col: int, direction: str):
        self.placed_words[word] = {'row': row, 'col': col, 'direction': direction}
        for i, letter in enumerate(word):
            if direction == 'horizontal': self.grid[row][col + i] = letter
            elif direction == 'vertical': self.grid[row + i][col] = letter
            elif direction == 'horizontal_rev': self.grid[row][col - i] = letter
            elif direction == 'vertical_rev': self.grid[row - i][col] = letter

    def _trim_grid(self):
        if not self.placed_words:
            self.grid, self.width, self.height = [], 0, 0
            return
        
        min_r, max_r, min_c, max_c = self.height, -1, self.width, -1

        for word, info in self.placed_words.items():
            r, c, d, l = info['row'], info['col'], info['direction'], len(word)
            min_r = min(min_r, r if d != 'vertical_rev' else r - l + 1)
            max_r = max(max_r, r if d != 'vertical' else r + l - 1)
            min_c = min(min_c, c if d != 'horizontal_rev' else c - l + 1)
            max_c = max(max_c, c if d != 'horizontal' else c + l - 1)

        min_r = max(0, min_r - 1)
        min_c = max(0, min_c - 1)
        max_r = min(self.height - 1, max_r + 1)
        max_c = min(self.width - 1, max_c + 1)

        self.grid = [row[min_c : max_c + 1] for row in self.grid[min_r : max_r + 1]]
        
        new_placed_words = {}
        for word, info in self.placed_words.items():
            new_placed_words[word] = {
                "row": info["row"] - min_r,
                "col": info["col"] - min_c,
                "direction": info["direction"]
            }
        self.placed_words = new_placed_words
        self.height = len(self.grid)
        self.width = len(self.grid[0]) if self.height > 0 else 0