import os
from typing import Dict, List, Tuple
from engligen.core.crossword import Crossword

class ClueGenerator:
    """
    Gera um arquivo .txt com a lista de dicas em texto puro,
    separadas por direções, e mantém um mapa das posições numeradas.
    """
    def __init__(self, crossword_obj: Crossword, clues_map: Dict[str, str]):
        self.crossword = crossword_obj
        self.clues_map = clues_map
        self.clue_positions: Dict[Tuple[int, int], List[Dict]] = {}
        self.word_clues: Dict[str, Dict] = {}
        
        # --- INÍCIO DA CORREÇÃO ---
        
        # 1. Inicializa o atributo que estava faltando
        self.numbering_map: Dict[Tuple[int, int], int] = {}

        # 2. Chama o método de geração para popular os dados imediatamente
        self._generate_clues()
        
        # --- FIM DA CORREÇÃO ---

    def _generate_clues(self):
        """
        Gera dicas e posições a partir da lista de palavras já colocadas,
        garantindo a correspondência correta e a numeração sequencial.
        """
        self.clue_positions.clear()
        self.word_clues.clear()
        self.numbering_map.clear() # Limpa o mapa a cada nova geração

        sorted_words = sorted(self.crossword.placed_words.items(), key=lambda item: (item[1]['row'], item[1]['col']))
        
        num = 1
        # Usa o atributo da classe (self.numbering_map) em vez de uma variável local
        for word, info in sorted_words:
            r, c = info['row'], info['col']
            
            if (r, c) in self.numbering_map:
                clue_num = self.numbering_map[(r, c)]
            else:
                clue_num = num
                self.numbering_map[(r, c)] = clue_num
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

    def generate_text_file(self, filename: str):
        """Gera o arquivo .txt com a lista de dicas."""
        # A geração de clues já foi feita no __init__, então não precisa chamar de novo
        
        output_dir = os.path.dirname(filename)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        dir_map = {
            "horizontal": "HORIZONTAL (Esquerda → Direita)",
            "vertical": "VERTICAL (Cima → Baixo)",
        }

        with open(filename, "w", encoding="utf-8") as f:
            for d_name, d_key in dir_map.items():
                words_in_dir = {w: d for w, d in self.word_clues.items() if d["direction"] == d_name}
                if not words_in_dir:
                    continue
                
                sorted_clues = sorted(words_in_dir.items(), key=lambda item: item[1]['num'])
                
                f.write(f"{d_key}\n")
                f.write(f"{'-'*len(d_key)}\n")
                for word, clue_data in sorted_clues:
                    f.write(f"{clue_data['num']}. {clue_data['clue']}\n")
                f.write("\n")

        print(f"📄 Arquivo de dicas '{os.path.basename(filename)}' gerado com sucesso!")