import random
import multiprocessing
import sys
from typing import List, Optional, Dict, Tuple, Set

# --- FUNÇÃO TRABALHADORA (definida fora da classe) ---
def _run_single_attempt(args: Tuple) -> Optional[Dict[str, Dict]]:
    """Executa uma única tentativa de geração num processo separado."""
    seed_word, other_words, themed_word_set, directions, full_word_list, max_size, target_density = args
    
    dynamic_grid: Dict[Tuple[int, int], str] = {}
    placed_words: Dict[str, Dict] = {}
    
    dr, dc = directions["horizontal"]
    placed_words[seed_word] = {"row": 0, "col": 0, "direction": "horizontal"}
    for i, char in enumerate(seed_word):
        dynamic_grid[(0, i * dc)] = char

    for word in other_words:
        if word in placed_words: continue
        
        # Passamos 'placed_words' para a função de busca para verificações mais inteligentes
        best_placement = _find_best_placement_for(word, dynamic_grid, directions, themed_word_set, max_size, placed_words)
        if best_placement:
            row, col, d_name = best_placement["row"], best_placement["col"], best_placement["direction"]
            dr, dc = directions[d_name]
            placed_words[word] = {"row": row, "col": col, "direction": d_name}
            for i, char in enumerate(word):
                dynamic_grid[(row + i * dr, col + i * dc)] = char

    # A função de preenchimento agora tem critérios de qualidade
    _fill_slots(dynamic_grid, placed_words, directions, full_word_list, themed_word_set, target_density, max_size)
    
    return placed_words

# --- Funções auxiliares ---

def _find_best_placement_for(word: str, grid: Dict, directions: Dict, themed_set: Set, max_size: Tuple[int, int], placed_words: Dict) -> Optional[Dict]:
    """Encontra a melhor posição para uma palavra, com verificações de qualidade aprimoradas."""
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
                    # --- MELHORIA 1: EVITAR SOBREPOSIÇÃO DE MESMA DIREÇÃO ---
                    # Verifica se a célula de cruzamento já pertence a uma palavra da mesma direção.
                    # Se sim, este posicionamento é inválido.
                    is_crossing_occupied = False
                    for p_word, p_info in placed_words.items():
                        if p_info['direction'] == d_name:
                            p_r, p_c = p_info['row'], p_info['col']
                            p_len = len(p_word)
                            p_dr, p_dc = directions[d_name]
                            if d_name == 'horizontal' and r == p_r and c >= p_c and c < p_c + p_len * p_dc:
                                is_crossing_occupied = True
                                break
                            if d_name == 'vertical' and c == p_c and r >= p_r and r < p_r + p_len * p_dr:
                                is_crossing_occupied = True
                                break
                    if is_crossing_occupied:
                        continue
                    # --- FIM DA MELHORIA 1 ---

                    row_start, col_start = r - i * dr, c - i * dc
                    if _can_place_dynamically(word, row_start, col_start, d_name, grid, directions, max_size, current_bounds):
                        score = _calculate_score(word, row_start, col_start, d_name, grid, directions, themed_set, current_bounds)
                        if not best_placement or score > best_placement["score"]:
                            best_placement = {"row": row_start, "col": col_start, "direction": d_name, "score": score}
    return best_placement

def _calculate_score(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, directions: Dict, themed_set: Set, bounds: Tuple) -> int:
    """Função de pontuação original, sem alterações."""
    dr, dc = directions[d_name]
    score = 5 if word in themed_set else 0
    min_r, max_r, min_c, max_c = bounds
    word_len = len(word)
    word_end_r, word_end_c = r_start + (word_len - 1) * dr, c_start + (word_len - 1) * dc
    
    if r_start < min_r or word_end_r < min_r or r_start > max_r or word_end_r > max_r or \
       c_start < min_c or word_end_c < min_c or c_start > max_c or word_end_c > max_c:
        score -= 2 

    for i, char in enumerate(word):
        r, c = r_start + i * dr, c_start + i * dc
        if grid.get((r, c)) == char: score += 2; continue
        if d_name == "horizontal":
            if grid.get((r - 1, c)): score += 1
            if grid.get((r + 1, c)): score += 1
        else:
            if grid.get((r, c - 1)): score += 1
            if grid.get((r, c + 1)): score += 1
    return score

def _can_place_dynamically(word: str, r_start: int, c_start: int, d_name: str, grid: Dict, directions: Dict, max_size: Tuple[int, int], bounds: Tuple) -> bool:
    """Função de verificação que impede aglomeração e paralelismo."""
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

    # --- CORREÇÃO: Bloco defeituoso que impedia a geração foi removido ---
    
    return True

def _fill_slots(grid: Dict, placed: Dict, directions: Dict, full_word_list: List[str], themed_word_set: Set, target_density: float, max_size: Tuple[int, int]):
    """Preenche apenas os espaços que criam novas conexões úteis."""
    themed_fill_words = [w for w in full_word_list if w in themed_word_set]
    common_fill_words = [w for w in full_word_list if w not in themed_word_set]
    prioritized_list = themed_fill_words + common_fill_words

    was_improved = True
    while was_improved:
        was_improved = False
        coords = list(grid.keys())
        if not coords: return
        
        min_r, max_r = min(r for r,c in coords), max(r for r,c in coords)
        min_c, max_c = min(c for r,c in coords), max(c for r,c in coords)

        current_width = max_c - min_c + 1
        current_height = max_r - min_r + 1
        total_cells = current_width * current_height
        if total_cells > 0 and (len(grid) / total_cells) >= target_density:
            break

        for d_name, (dr, dc) in directions.items():
            if d_name == 'horizontal':
                outer_range, inner_range = range(min_r, max_r + 1), range(min_c - 1, max_c + 2)
            else:
                outer_range, inner_range = range(min_c, max_c + 1), range(min_r - 1, max_r + 2)

            for fixed_axis_val in outer_range:
                slot_start_coord = -1
                for scan_axis_val in inner_range:
                    r, c = (fixed_axis_val, scan_axis_val) if d_name == 'horizontal' else (scan_axis_val, fixed_axis_val)
                    
                    if grid.get((r, c)) is None:
                        if slot_start_coord == -1: slot_start_coord = scan_axis_val
                    else:
                        if slot_start_coord != -1:
                            length = scan_axis_val - slot_start_coord
                            if length > 2:
                                s_r, s_c = (fixed_axis_val, slot_start_coord) if d_name == 'horizontal' else (slot_start_coord, fixed_axis_val)
                                
                                # --- MELHORIA 2: VERIFICAR QUALIDADE DA CONEXÃO ---
                                # Só preenche o espaço se a nova palavra for cruzar com uma existente.
                                creates_connection = False
                                for i in range(length):
                                    check_r, check_c = s_r + i * dr, s_c + i * dc
                                    perp_dr, perp_dc = directions['vertical' if d_name == 'horizontal' else 'horizontal']
                                    if grid.get((check_r - perp_dr, check_c - perp_dc)) or grid.get((check_r + perp_dr, check_c + perp_dc)):
                                        creates_connection = True
                                        break
                                
                                if not creates_connection:
                                    slot_start_coord = -1
                                    continue # Pula para o próximo espaço se não criar conexão.
                                # --- FIM DA MELHORIA 2 ---

                                pattern = "".join([grid.get((s_r + i * dr, s_c + i * dc)) or '.' for i in range(length)])
                                for word in prioritized_list:
                                    # Corrigido para lidar com o dicionário 'placed' que pode não ter a chave 'word'
                                    if len(word) == length and word not in placed and '.' not in pattern:
                                        placed[word] = {"row": s_r, "col": s_c, "direction": d_name}
                                        for i, char in enumerate(word): grid[(s_r + i * dr, s_c + i * dc)] = char
                                        was_improved = True
                                        break
                            slot_start_coord = -1
                        if was_improved: break
                if was_improved: break
            if was_improved: break

# --- CLASSE PRINCIPAL (Sem alterações) ---
class Crossword:
    def __init__(self, themed_words: List[str], common_words: List[str], num_attempts: int = 50, max_size: Tuple[int, int] = (30, 30), target_density: float = 0.7):
        self.themed_words = sorted(list(set(w.upper() for w in themed_words if len(w) > 2)), key=len, reverse=True)
        self.common_words = sorted(list(set(w.upper() for w in common_words if len(w) > 2)), key=len, reverse=True)
        self.themed_word_set = set(self.themed_words)
        self.full_word_list = self.themed_words + self.common_words
        random.shuffle(self.full_word_list)
        
        self.num_attempts = num_attempts
        self.max_size = max_size
        self.target_density = target_density
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
            # Adiciona o nome da palavra ao dicionário para referência futura
            for w in other_words:
                if w in self.placed_words:
                    self.placed_words[w]['word'] = w
            tasks_args.append((seed, other_words, self.themed_word_set, self.directions, self.full_word_list, self.max_size, self.target_density))

        print(f"⚙️  Executando {len(tasks_args)} tentativas em paralelo (limite: {self.max_size[0]}x{self.max_size[1]}, densidade alvo: {self.target_density:.0%})...")
        results = []
        try:
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
        except (ImportError, OSError, AttributeError):
            print("\n⚠️  Aviso: Multiprocessing não pôde ser iniciado. Executando em modo sequencial (mais lento).")
            for args in tasks_args:
                result = _run_single_attempt(args)
                if result:
                    results.append(result)
        print("\n")

        successful_results = [res for res in results if res]
        if not successful_results: 
            print("❌ FALHA: Nenhuma grade válida encontrada. Tente novamente ou ajuste os bancos de palavras.")
            return False

        best_placed_words = max(successful_results, key=len)
        print(f"✨ Melhor resultado encontrado com {len(best_placed_words)} palavras.")
        self.placed_words = best_placed_words
        self._finalize_grid()
        return True

    def _finalize_grid(self):
        if not self.placed_words: return

        all_rows, all_cols = [], []
        for word, info in self.placed_words.items():
            r_start, c_start, d = info['row'], info['col'], info['direction']
            dr, dc = self.directions[d]
            for i in range(len(word)):
                all_rows.append(r_start + i * dr)
                all_cols.append(c_start + i * dc)

        min_r, max_r = min(all_rows), max(all_rows)
        min_c, max_c = min(all_cols), max(all_cols)
        
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
