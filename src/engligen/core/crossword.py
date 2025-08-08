import random
import multiprocessing
import sys
from typing import List, Optional, Dict, Tuple, Set

# --- FUNÇÃO TRABALHADORA (definida fora da classe) ---
def _run_single_attempt(args: Tuple) -> Optional[Dict[str, Dict]]:
    """Executa uma única tentativa de geração num processo separado."""
    seed_word, other_words, themed_word_set, directions, full_word_list = args
    
    dynamic_grid: Dict[Tuple[int, int], str] = {}
    placed_words: Dict[str, Dict] = {}
    
    # 1. Coloca a palavra semente
    dr, dc = directions["horizontal"]
    placed_words[seed_word] = {"row": 0, "col": 0, "direction": "horizontal"}
    for i, char in enumerate(seed_word):
        dynamic_grid[(0, i * dc)] = char

    # 2. Tenta colocar as outras palavras
    for word in other_words:
        if word in placed_words: continue
        
        best_placement = _find_best_placement_for(word, dynamic_grid, directions, themed_word_set)
        if best_placement:
            row, col, d_name = best_placement["row"], best_placement["col"], best_placement["direction"]
            dr, dc = directions[d_name]
            placed_words[word] = {"row": row, "col": col, "direction": d_name}
            for i, char in enumerate(word):
                dynamic_grid[(row + i * dr, col + i * dc)] = char

    # 3. Executa o passo de Slot-Filling
    # CORREÇÃO DO BUG ESTÁ AQUI: Usamos o 'full_word_list' que foi passado nos argumentos
    _fill_slots(dynamic_grid, placed_words, directions, full_word_list)
    
    return placed_words

# --- Funções auxiliares para a função trabalhadora (permanecem as mesmas) ---

def _find_best_placement_for(word: str, grid: Dict, directions: Dict, themed_set: Set) -> Optional[Dict]:
    best_placement = None
    for i, letter in enumerate(word):
        for (r, c), char_in_grid in grid.items():
            if char_in_grid == letter:
                for d_name, (dr, dc) in directions.items():
                    row_start, col_start = r - i * dr, c - i * dc
                    if _can_place_dynamically(word, row_start, col_start, d_name, grid, directions):
                        score = _calculate_score(word, row_start, col_start, d_name, grid, directions, themed_set)
                        if not best_placement or score > best_placement["score"]:
                            best_placement = {"row": row_start, "col": col_start, "direction": d_name, "score": score}
    return best_placement

def _calculate_score(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, directions: Dict, themed_set: Set) -> int:
    dr, dc = directions[d_name]
    score = 5 if word in themed_set else 0
    for i, char in enumerate(word):
        r, c = r_start + i * dr, c_start + i * dc
        if grid.get((r, c)) == char:
            score += 2
            continue
        if d_name == "horizontal":
            if grid.get((r - 1, c)): score += 1
            if grid.get((r + 1, c)): score += 1
        else:
            if grid.get((r, c - 1)): score += 1
            if grid.get((r, c + 1)): score += 1
    return score

def _can_place_dynamically(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, directions: Dict) -> bool:
    dr, dc = directions[d_name]
    for i, char in enumerate(word):
        r, c = r_start + i * dr, c_start + i * dc
        if grid.get((r, c), char) != char: return False
        if grid.get((r, c)) != char:
            if d_name == "horizontal" and (grid.get((r - 1, c)) or grid.get((r + 1, c))): return False
            if d_name == "vertical" and (grid.get((r, c - 1)) or grid.get((r, c + 1))): return False
    r_before, c_before = r_start - dr, c_start - dc
    if grid.get((r_before, c_before)): return False
    r_after, c_after = r_start + len(word) * dr, c_start + len(word) * dc
    if grid.get((r_after, c_after)): return False
    return True

def _fill_slots(grid: Dict, placed: Dict, directions: Dict, full_word_list: List[str]):
    was_improved = True
    while was_improved:
        was_improved = False
        coords = list(grid.keys())
        if not coords: return
        min_r, max_r = min(r for r, c in coords), max(r for r, c in coords)
        min_c, max_c = min(c for r, c in coords), max(c for r, c in coords)

        for d_name, (dr, dc) in directions.items():
            for main_axis in range(min_r if d_name == 'horizontal' else min_c, (max_r if d_name == 'horizontal' else max_c) + 1):
                slot_start = -1
                for second_axis in range((min_c if d_name == 'horizontal' else min_r) -1, (max_c if d_name == 'horizontal' else max_r) + 2):
                    r, c = (main_axis, second_axis) if d_name == 'horizontal' else (second_axis, main_axis)
                    if grid.get((r, c)) is None:
                        if slot_start == -1: slot_start = second_axis
                    else:
                        if slot_start != -1:
                            length = second_axis - slot_start
                            if length > 2:
                                s_r, s_c = (main_axis, slot_start) if d_name == 'horizontal' else (slot_start, main_axis)
                                pattern = "".join([grid.get((s_r + i * dr, s_c + i * dc)) or '.' for i in range(length)])
                                for word in full_word_list:
                                    if len(word) == length and word not in placed:
                                        if all(pattern[i] in ('.', char) for i, char in enumerate(word)):
                                            # Place word
                                            placed[word] = {"row": s_r, "col": s_c, "direction": d_name}
                                            for i, char in enumerate(word): grid[(s_r + i * dr, s_c + i * dc)] = char
                                            was_improved = True
                                            break
                            slot_start = -1
                        if was_improved: break
                if was_improved: break

# --- CLASSE PRINCIPAL ---
class Crossword:
    def __init__(self, themed_words: List[str], common_words: List[str], num_attempts: int = 50):
        self.themed_words = sorted(list(set(w.upper() for w in themed_words if len(w) > 2)), key=len, reverse=True)
        self.common_words = sorted(list(set(w.upper() for w in common_words if len(w) > 2)), key=len, reverse=True)
        self.themed_word_set = set(self.themed_words)
        self.full_word_list = self.themed_words + self.common_words
        self.num_attempts = num_attempts
        self.directions = {"horizontal": (0, 1), "vertical": (1, 0)}
        self.grid: List[List[Optional[str]]] = []
        self.placed_words: Dict[str, Dict] = {}
        self.width, self.height = 0, 0

    def generate(self) -> bool:
        words_to_try_as_seed = self.themed_words[:self.num_attempts]
        if not words_to_try_as_seed:
            print("❌ ERRO: Nenhuma palavra temática longa o suficiente para iniciar a geração.")
            return False

        tasks_args = []
        for seed in words_to_try_as_seed:
            other_words = [w for w in self.full_word_list if w != seed]
            random.shuffle(other_words)
            tasks_args.append((seed, other_words, self.themed_word_set, self.directions, self.full_word_list))

        print(f"⚙️  Executando {len(tasks_args)} tentativas em paralelo...")
        
        results = []
        with multiprocessing.Pool() as pool:
            # NOVIDADE: Usamos imap_unordered para obter resultados à medida que ficam prontos
            imap_results = pool.imap_unordered(_run_single_attempt, tasks_args)
            
            for i, result in enumerate(imap_results):
                # Desenha a barra de progresso
                progress = (i + 1) / len(tasks_args)
                bar_length = 30
                filled_length = int(bar_length * progress)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                sys.stdout.write(f'\r   Progresso: |{bar}| {i+1}/{len(tasks_args)} Concluído')
                sys.stdout.flush()
                
                if result:
                    results.append(result)
        
        print("\n") # Nova linha após a barra de progresso

        successful_results = [res for res in results if res]
        if not successful_results:
            return False

        best_placed_words = max(successful_results, key=len)
        
        print(f"✨ Melhor resultado encontrado com {len(best_placed_words)} palavras.")
        
        self.placed_words = best_placed_words
        self._finalize_grid()
        return True

    def _finalize_grid(self):
        if not self.placed_words: return
        coords = self.placed_words.values()
        min_r = min(p['row'] for p in coords)
        max_r = max(p['row'] + (len(word) - 1 if p['direction'] == 'vertical' else 0) for word, p in self.placed_words.items())
        min_c = min(p['col'] for p in coords)
        max_c = max(p['col'] + (len(word) - 1 if p['direction'] == 'horizontal' else 0) for word, p in self.placed_words.items())
        min_r, max_r = min_r - 1, max_r + 1
        min_c, max_c = min_c - 1, max_c + 1
        self.height, self.width = max_r - min_r + 1, max_c - min_c + 1
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        final_placed_words = {}
        for word, info in self.placed_words.items():
            r, c, d = info['row'], info['col'], info['direction']
            new_r, new_c = r - min_r, c - min_c
            final_placed_words[word] = {"row": new_r, "col": new_c, "direction": d}
            dr, dc = self.directions[d]
            for i, char in enumerate(word):
                self.grid[new_r + i * dr][new_c + i * dc] = char
        self.placed_words = final_placed_words