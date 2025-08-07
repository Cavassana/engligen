# src/engligen/rendering/clue_generator.py

from typing import Dict, List, Tuple
import os
from engligen.core.crossword import Crossword

class ClueGenerator:
    """
    Gera um arquivo .txt com a lista de dicas em texto puro,
    separadas por Horizontal e Vertical.
    """
    def __init__(self, crossword_obj: Crossword, clues_map: Dict[str, str]):
        self.crossword = crossword_obj
        self.clues_map = clues_map
        # Mapeia a posição (r, c) de uma CÉLULA DE DICA para as informações da dica
        self.clue_positions: Dict[Tuple[int, int], List[Dict]] = {}
        # Mapeia cada PALAVRA para seu número e dica
        self.word_clues: Dict[str, Dict] = {}

    def _get_word_start_position(self, word: str, info: Dict) -> Tuple[int, int]:
        """Retorna a posição inicial real da palavra na grade."""
        row, col, direction = info['row'], info['col'], info['direction']
        word_len = len(word)
        
        if direction == 'horizontal':
            return (row, col)  # Posição já é o início
        elif direction == 'vertical':
            return (row, col)  # Posição já é o início
        elif direction == 'horizontal_rev':
            return (row, col - word_len + 1)  # Início real é word_len-1 posições antes
        elif direction == 'vertical_rev':
            return (row - word_len + 1, col)  # Início real é word_len-1 posições acima
        
        return (row, col)

    def _generate_clues(self):
        """Associa cada palavra a um número e mapeia a posição da sua célula de dica."""
        
        # Coleta todas as posições de início das palavras
        word_starts = []
        for word, info in self.crossword.placed_words.items():
            start_row, start_col = self._get_word_start_position(word, info)
            word_starts.append({
                'word': word,
                'start_row': start_row,
                'start_col': start_col,
                'direction': info['direction'],
                'info': info
            })
        
        # Ordena por posição (linha primeiro, depois coluna) para numeração sequencial
        word_starts.sort(key=lambda x: (x['start_row'], x['start_col']))
        
        # Atribui números sequenciais e mapeia posições das células de dica
        for i, word_data in enumerate(word_starts):
            word = word_data['word']
            start_row = word_data['start_row']
            start_col = word_data['start_col']
            direction = word_data['direction']
            
            # Número sequencial único
            clue_number = i + 1
            
            # Armazena informações da dica para a palavra
            self.word_clues[word] = {
                'num': clue_number, 
                'clue': self.clues_map.get(word, ""),
                'direction': direction
            }

            # A célula de dica é ANTES da posição inicial da palavra
            clue_pos = None
            if direction == 'horizontal': clue_pos = (start_row, start_col)
            elif direction == 'vertical': clue_pos = (start_row, start_col)
            elif direction == 'horizontal_rev': clue_pos = (start_row, start_col)
            elif direction == 'vertical_rev': clue_pos = (start_row, start_col)
    
            # Adiciona a dica na posição correspondente (se válida)
            if clue_pos and 0 <= clue_pos[0] < self.crossword.height and 0 <= clue_pos[1] < self.crossword.width:
                if clue_pos not in self.clue_positions:
                    self.clue_positions[clue_pos] = []
                
                self.clue_positions[clue_pos].append({
                    'num': str(clue_number), 
                    'dir': direction
                })

    def generate_text_file(self, filename: str = "crossword_clues.txt"):
        """Gera o arquivo .txt com a lista de dicas."""
        self._generate_clues()

        dir_map = {
            'horizontal': "HORIZONTAL (Esquerda → Direita)",
            'vertical': "VERTICAL (Cima → Baixo)",
            'horizontal_rev': "HORIZONTAL (Direita → Esquerda)",
            'vertical_rev': "VERTICAL (Baixo → Cima)"
        }
        
        output_dir = "output"
        if not os.path.exists(output_dir): 
            os.makedirs(output_dir)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for d_key, d_name in dir_map.items():
                # Filtra palavras por direção e ordena por número
                words_in_dir = [
                    word for word, clue_data in self.word_clues.items() 
                    if clue_data['direction'] == d_key
                ]
                words_in_dir.sort(key=lambda w: self.word_clues[w]['num'])
                
                if not words_in_dir: 
                    continue  # Pula se não houver palavras para a direção

                f.write(f"{d_name}\n{'-' * len(d_name)}\n")
                for word in words_in_dir:
                    clue_data = self.word_clues[word]
                    f.write(f"{clue_data['num']}. {clue_data['clue']}\n")
                f.write("\n")
            
        print(f"Arquivo de dicas '{filepath}' gerado com sucesso!")