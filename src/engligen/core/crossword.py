import random
import multiprocessing
import sys
from typing import List, Optional, Dict, Tuple, Set

# --- NOVA FUNÇÃO DE VERIFICAÇÃO ---
def _is_start_cell_adjacent_to_same_direction(r_start: int, c_start: int, d_name: str, placed_words: Dict[str, Dict]) -> bool:
    """Verifica se a célula inicial proposta é adjacente a outra célula inicial da mesma direção."""
    # Células vizinhas a serem verificadas
    adjacent_cells_to_check = [
        (r_start, c_start + 1),
        (r_start, c_start - 1),
        (r_start + 1, c_start),
        (r_start - 1, c_start)
    ]

    for info in placed_words.values():
        # A verificação só se aplica se a palavra existente tiver a MESMA direção
        if info['direction'] == d_name:
            if (info['row'], info['col']) in adjacent_cells_to_check:
                return True  # Encontrou um início adjacente na mesma direção
    return False

# --- FUNÇÃO TRABALHADORA (definida fora da classe) ---
def _run_single_attempt(args: Tuple) -> Optional[Dict[str, Dict]]:
    """Executa uma única tentativa de geração num processo separado."""
    seed_word, other_words, themed_word_set, directions, full_word_list, max_size = args
    
    dynamic_grid: Dict[Tuple[int, int], str] = {}
    placed_words: Dict[str, Dict] = {}
    
    dr, dc = directions["horizontal"]
    placed_words[seed_word] = {"row": 0, "col": 0, "direction": "horizontal"}
    for i, char in enumerate(seed_word):
        dynamic_grid[(0, i * dc)] = char

    for word in other_words:
        if word in placed_words: continue
        
        # Passamos 'placed_words' para a função de busca
        best_placement = _find_best_placement_for(word, dynamic_grid, directions, themed_word_set, max_size, placed_words)
        
        if best_placement:
            row, col, d_name = best_placement["row"], best_placement["col"], best_placement["direction"]
            dr, dc = directions[d_name]
            placed_words[word] = {"row": row, "col": col, "direction": d_name}
            for i, char in enumerate(word):
                dynamic_grid[(row + i * dr, col + i * dc)] = char
    
    return placed_words

# --- Funções auxiliares ---

def _find_best_placement_for(word: str, grid: Dict, directions: Dict, themed_set: Set, max_size: Tuple[int, int], placed_words: Dict) -> Optional[Dict]:
    """Encontra a melhor posição para uma palavra, agora verificando inícios adjacentes."""
    best_placement = None
    coords = list(grid.keys())
    if not coords:
        min_r, max_r, min_c, max_c = 0,0,0,0
    else:
        min_r, max_r = min(r for r, c in coords), max(r for r, c in coords)
        min_c, max_c = min(c for r, c in coords), max(c for r, c in coords)
    current_bounds = (min_r, max_r, min_c, max_c)

    for i, letter in enumerate(word):
        for (r, c), char_in_grid in grid.items():
            if char_in_grid == letter:
                for d_name, (dr, dc) in directions.items():
                    row_start, col_start = r - i * dr, c - i * dc
                    
                    # Realiza as duas verificações em sequência
                    can_place = _can_place_dynamically(word, row_start, col_start, d_name, grid, directions, max_size, current_bounds)
                    start_is_clear = not _is_start_cell_adjacent_to_same_direction(row_start, col_start, d_name, placed_words)

                    if can_place and start_is_clear:
                        score = _calculate_score(word, row_start, col_start, d_name, grid, themed_set)
                        if not best_placement or score > best_placement["score"]:
                            best_placement = {"row": row_start, "col": col_start, "direction": d_name, "score": score}
    return best_placement

def _calculate_score(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, themed_set: Set) -> int:
    dr, dc = directions[d_name]
    score = 10 if word in themed_set else 1

    for i, char in enumerate(word):
        r, c = r_start + i * dr, c_start + i * dc
        if grid.get((r, c)) == char: score += 3; continue
        if d_name == "horizontal":
            if grid.get((r - 1, c)) or grid.get((r + 1, c)): score += 1
        else: # vertical
            if grid.get((r, c - 1)) or grid.get((r, c + 1)): score += 1
    return score

def _can_place_dynamically(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, directions: Dict, max_size: Tuple[int, int], bounds: Tuple) -> bool:
    max_h, max_w = max_size
    min_r, max_r, min_c, max_c = bounds
    dr, dc = directions[d_name]
    word_len = len(word)
    
    word_end_r, word_end_c = r_start + (word_len - 1) * dr, c_start + (word_len - 1) * dc
    new_min_r, new_max_r = min(min_r, r_start, word_end_r), max(max_r, r_start, word_end_r)
    new_min_c, new_max_c = min(min_c, c_start, word_end_c), max(max_c, c_start, word_end_c)

    if (new_max_r - new_min_r + 1) > max_h or (new_max_c - new_min_c + 1) > max_w:
        return False

    r_before, c_before = r_start - dr, c_start - dc
    if grid.get((r_before, c_before)): 
        return False
    
    r_after, c_after = r_start + word_len * dr, c_start + word_len * dc
    if grid.get((r_after, c_after)): 
        return False

    for i, char in enumerate(word):
        r, c = r_start + i * dr, c_start + i * dc
        if grid.get((r, c), char) != char: return False
        if grid.get((r, c)) != char:
            if d_name == "horizontal" and (grid.get((r - 1, c)) or grid.get((r + 1, c))): return False
            if d_name == "vertical" and (grid.get((r, c - 1)) or grid.get((r, c + 1))): return False
    return True

# --- CLASSE PRINCIPAL ---
class Crossword:
    def __init__(self, themed_words: List[str], common_words: List[str], num_attempts: int = 100):
        self.height, self.width = 20, 15
        self.max_size = (self.height - 2, self.width - 2)
        
        self.themed_words = sorted(list(set(w.upper() for w in themed_words if 2 < len(w) <= self.max_size[1])), key=len, reverse=True)
        self.common_words = sorted(list(set(w.upper() for w in common_words if 2 < len(w) <= self.max_size[1])), key=len, reverse=True)
        self.themed_word_set = set(self.themed_words)
        self.full_word_list = self.themed_words + self.common_words
        self.num_attempts = num_attempts
        self.directions = {"horizontal": (0, 1), "vertical": (1, 0)}
        
        self.grid: List[List[Optional[str]]] = []
        self.placed_words: Dict[str, Dict] = {}

    def generate(self) -> bool:
        words_to_try_as_seed = self.themed_words[:self.num_attempts]
        if not words_to_try_as_seed:
            print("❌ ERRO: Nenhuma palavra temática longa o suficiente para iniciar a geração.")
            return False
            
        tasks_args = []
        for seed in words_to_try_as_seed:
            other_words = [w for w in self.full_word_list if w != seed]
            random.shuffle(other_words)
            tasks_args.append((seed, other_words, self.themed_word_set, self.directions, self.full_word_list, self.max_size))

        print(f"⚙️  Executando {len(tasks_args)} tentativas em paralelo...")
        results = []
        with multiprocessing.Pool() as pool:
            imap_results = pool.imap_unordered(_run_single_attempt, tasks_args)
            for i, result in enumerate(imap_results):
                progress = (i + 1) / len(tasks_args)
                bar_length = 30
                filled_length = int(bar_length * progress)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                sys.stdout.write(f'\r   Progresso: |{bar}| {i+1}/{len(tasks_args)} Concluído')
                sys.stdout.flush()
                if result:
                    results.append(result)
        print("\n")

        valid_results = []
        for result in results:
            if not result: continue
            themed_count = sum(1 for word in result if word in self.themed_word_set)
            total_count = len(result)
            if total_count > 0 and (themed_count / total_count) >= 0.5:
                valid_results.append(result)
        
        print(f"📊 Encontrados {len(valid_results)} resultados com pelo menos 50% de palavras temáticas.")

        if not valid_results: 
            print("❌ FALHA: Nenhuma grade válida encontrada que cumpra os critérios. Tente novamente ou ajuste os bancos de palavras.")
            return False

        best_placed_words = max(valid_results, key=len)
        print(f"✨ Melhor resultado encontrado com {len(best_placed_words)} palavras.")
        
        self.placed_words = best_placed_words
        self._finalize_grid()
        return True

    def _finalize_grid(self):
        if not self.placed_words: return
        
        all_rows = []
        all_cols = []
        for word, info in self.placed_words.items():
            r, c, d = info['row'], info['col'], info['direction']
            dr, dc = self.directions[d]
            for i in range(len(word)):
                all_rows.append(r + i * dr)
                all_cols.append(c + i * dc)

        min_r, max_r = min(all_rows), max(all_rows)
        min_c, max_c = min(all_cols), max(all_cols)
        
        block_height = max_r - min_r + 1
        block_width = max_c - min_c + 1

        offset_r = ((self.height - block_height) // 2) - min_r
        offset_c = ((self.width - block_width) // 2) - min_c

        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        final_placed_words = {}
        for word, info in self.placed_words.items():
            r, c, d = info['row'], info['col'], info['direction']
            new_r, new_c = r + offset_r, c + offset_c
            final_placed_words[word] = {"row": new_r, "col": new_c, "direction": d}
            dr, dc = self.directions[d]
            for i, char in enumerate(word):
                if 0 <= (new_r + i * dr) < self.height and 0 <= (new_c + i * dc) < self.width:
                    self.grid[new_r + i * dr][new_c + i * dc] = char
        self.placed_words = final_placed_words