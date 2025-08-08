import os
from typing import Dict, List, Tuple
from engligen.core.crossword import Crossword

class ClueGenerator:
    """
    Gera um arquivo .txt com a lista de dicas em texto puro,
    separadas por quatro direções, e mantém um mapa de posições das dicas.
    """
    def __init__(self, crossword_obj: Crossword, clues_map: Dict[str, str]):
        self.crossword = crossword_obj
        self.clues_map = clues_map
        self.clue_positions: Dict[Tuple[int, int], List[Dict]] = {}
        self.word_clues: Dict[str, Dict] = {}

    def _generate_clues(self):
        """
        Gera dicas e posições a partir da lista de palavras já colocadas,
        garantindo a correspondência correta e a numeração sequencial.
        """
        self.clue_positions.clear()
        self.word_clues.clear()

        # Ordena as palavras pela posição para uma numeração lógica
        sorted_words = sorted(self.crossword.placed_words.items(), key=lambda item: (item[1]['row'], item[1]['col']))
        
        num = 1
        numbered_cells = {}

        for word, info in sorted_words:
            r, c = info['row'], info['col']
            
            # Reutiliza o número se a célula já tiver um
            if (r, c) in numbered_cells:
                clue_num = numbered_cells[(r, c)]
            else:
                clue_num = num
                numbered_cells[(r, c)] = clue_num
                num += 1

            self.word_clues[word] = {
                "num": clue_num,
                "clue": self.clues_map.get(word, f"Dica para '{word}' não encontrada."),
                "direction": info['direction'],
            }
            
            self.clue_positions.setdefault((r, c), []).append({
                "num": str(clue_num), 
                "dir": info['direction']
            })

    def generate_text_file(self, filename: str = "crossword_clues.txt"):
        """Gera o arquivo .txt com a lista de dicas em quatro seções."""
        self._generate_clues()
        os.makedirs("output", exist_ok=True)
        
        dir_map = {
            "horizontal": "HORIZONTAL (Esquerda → Direita)",
            "vertical": "VERTICAL (Cima → Baixo)",
            "horizontal_rev": "HORIZONTAL (Direita → Esquerda)",
            "vertical_rev": "VERTICAL (Baixo → Cima)",
        }

        with open(os.path.join("output", filename), "w", encoding="utf-8") as f:
            for d_name, d_key in dir_map.items():
                # Filtra palavras para a direção atual
                words_in_dir = {w: d for w, d in self.word_clues.items() if d["direction"] == d_name}
                if not words_in_dir:
                    continue
                
                # Ordena as palavras pelo número da dica
                sorted_clues = sorted(words_in_dir.items(), key=lambda item: item[1]['num'])
                
                f.write(f"{d_key}\n")
                f.write(f"{'-'*len(d_key)}\n")
                for word, clue_data in sorted_clues:
                    f.write(f"{clue_data['num']}. {clue_data['clue']}\n")
                f.write("\n")

        print(f"Arquivo de dicas '{filename}' gerado com sucesso!")