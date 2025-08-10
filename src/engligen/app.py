import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Set

# Importa as classes do projeto
from engligen.core.crossword import Crossword
from engligen.core.word_search import WordSearch
from engligen.rendering.clue_generator import ClueGenerator
from engligen.rendering.crossword_renderer import CrosswordRenderer
from engligen.rendering.wordsearch_renderer import WordSearchRenderer

class EngligenApp:
    """
    Classe que orquestra a lógica principal para gerar exercícios,
    separando a lógica de negócio da interface do usuário.
    """
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.caminho_palavras_usadas = self.project_root / "data" / "wordlists" / "used_words.json"
        self.default_paths = self._load_default_paths()

    def _load_default_paths(self) -> Dict[str, str]:
        """Carrega os caminhos padrão do arquivo de configuração."""
        try:
            with open("data/config.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _carregar_dados_palavras(self, caminho_arquivo: str) -> Optional[List[Dict]]:
        """Carrega os dados de um arquivo JSON de palavras."""
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ ERRO ao ler o arquivo JSON '{caminho_arquivo}': {e}")
            return None

    def _carregar_palavras_usadas(self) -> Set[str]:
        """Carrega o conjunto de palavras já utilizadas de um arquivo JSON."""
        if not self.caminho_palavras_usadas.exists():
            return set()
        try:
            with open(self.caminho_palavras_usadas, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            return set()

    def _salvar_palavras_usadas(self, palavras_novas: Set[str], palavras_antigas: Set[str]):
        """Adiciona novas palavras usadas à lista e salva no arquivo JSON."""
        palavras_atualizadas = palavras_antigas.union(palavras_novas)
        self.caminho_palavras_usadas.parent.mkdir(parents=True, exist_ok=True)
        with open(self.caminho_palavras_usadas, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(palavras_atualizadas)), f, indent=4)
        print(f"✔️  Banco de palavras usadas atualizado com {len(palavras_novas)} novas palavras.")

    def executar_gerador_crossword(self, output_basename: str, altura: int, largura: int, seed: Optional[int], reset: bool):
        """Lógica completa para gerar as palavras cruzadas."""
        themed_words_file = self.default_paths.get("themed_words_file")
        common_words_file = self.default_paths.get("common_words_file")

        if not themed_words_file or not common_words_file:
            print("❌ ERRO: Arquivos de palavras (tema e curinga) não definidos em 'data/config.json'.")
            return

        if reset and self.caminho_palavras_usadas.exists():
            self.caminho_palavras_usadas.unlink()
            print("🗑️  Histórico de palavras usadas foi limpo.")

        if seed is not None:
            random.seed(seed)
            print(f"🎯 Seed configurada: {seed}")

        print("⚙️  Iniciando a geração do exercício de Palavras Cruzadas...")
        themed_data = self._carregar_dados_palavras(themed_words_file)
        common_data = self._carregar_dados_palavras(common_words_file)
        if not themed_data or not common_data: return

        palavras_usadas = self._carregar_palavras_usadas()
        original_themed_set = {item['word'].upper() for item in themed_data}
        original_common_set = {item['word'].upper() for item in common_data}
        themed_list_disponivel = list(original_themed_set - palavras_usadas)
        common_list_disponivel = list(original_common_set - palavras_usadas)
        all_words_data = themed_data + common_data
        clues_map = {item['word'].upper(): item['clue'] for item in all_words_data}

        if not themed_list_disponivel:
            print("❌ ERRO: Não há palavras temáticas disponíveis.")
            return

        crossword_puzzle = Crossword(themed_words=themed_list_disponivel, common_words=common_list_disponivel, max_size=(altura, largura))
        if not crossword_puzzle.generate():
            print("\n❌ FALHA: O algoritmo não conseguiu encontrar uma solução válida.")
            return

        print(f"✅ SUCESSO! Melhor grade encontrada com {len(crossword_puzzle.placed_words)} palavras.")
        
        print("\n📦 Gerando arquivos de saída...")
        os.makedirs("output", exist_ok=True)
        self._salvar_palavras_usadas(set(crossword_puzzle.placed_words.keys()), palavras_usadas)

        clue_generator = ClueGenerator(crossword_puzzle, clues_map)
        crossword_renderer = CrosswordRenderer(crossword_puzzle, clue_generator)
        
        clue_generator.generate_text_file(filename=f"output/{output_basename}_clues.txt")
        crossword_renderer.generate_image(filename=f"output/{output_basename}_exercicio.png", answers=False)
        crossword_renderer.generate_image(filename=f"output/{output_basename}_respostas.png", answers=True)

        print(f"\n🎉 Tudo pronto! Verifique a pasta 'output'.")

    def executar_gerador_wordsearch(self, output_basename: str, size: int):
        """Lógica completa para gerar o caça-palavras."""
        themed_words_file = self.default_paths.get("themed_words_file")
        common_words_file = self.default_paths.get("common_words_file")

        if not themed_words_file or not common_words_file:
            print("❌ ERRO: Arquivos de palavras não definidos em 'data/config.json'.")
            return

        print("⚙️  Iniciando a geração do exercício de Caça-Palavras...")
        themed_data = self._carregar_dados_palavras(themed_words_file)
        common_data = self._carregar_dados_palavras(common_words_file)
        if not themed_data or not common_data: return
        
        all_words_data = themed_data + common_data
        clues_map = {item['word'].upper(): item['clue'] for item in all_words_data}

        palavras_usadas_crossword = self._carregar_palavras_usadas()
        original_themed_set = {item['word'].upper() for item in themed_data}
        palavras_restantes = list(original_themed_set - palavras_usadas_crossword)
        
        if not palavras_restantes:
            print("ℹ️  Nenhuma palavra temática restante para gerar o caça-palavras.")
            return

        print(f"✔️  {len(palavras_restantes)} palavras restantes serão usadas.")

        word_search_puzzle = WordSearch(words=palavras_restantes, size=size)
        if not word_search_puzzle.generate():
            print("\n❌ FALHA: O algoritmo não conseguiu gerar o caça-palavras.")
            return

        print(f"✅ SUCESSO! Caça-palavras gerado com {len(word_search_puzzle.placed_words)} palavras.")
        
        print("\n📦 Gerando arquivos de saída...")
        output_folder = self.project_root / "output"
        output_folder.mkdir(exist_ok=True)

        # --- INÍCIO DA ALTERAÇÃO ---

        # Gera o arquivo de texto com DICAS NUMERADAS para consistência
        clues_path = output_folder / f"{output_basename}_clues.txt"
        with open(clues_path, 'w', encoding='utf-8') as f:
            header = "DICAS"
            f.write(f"{header}\n")
            f.write(f"{'-'*len(header)}\n")
            
            placed_words_list = sorted(list(word_search_puzzle.placed_words.keys()))
            
            for i, word in enumerate(placed_words_list, 1):
                clue = clues_map.get(word, f"Dica para '{word}' não encontrada.")
                f.write(f"{i}. {clue}\n")
        
        print(f"📄 Arquivo de dicas '{clues_path.name}' gerado com sucesso!")

        # --- FIM DA ALTERAÇÃO ---
        
        renderer = WordSearchRenderer(word_search_puzzle)
        renderer.generate_image(filename=f"output/{output_basename}_exercicio.png", answers=False)
        renderer.generate_image(filename=f"output/{output_basename}_respostas.png", answers=True)

        print(f"\n🎉 Tudo pronto! Verifique a pasta 'output'.")