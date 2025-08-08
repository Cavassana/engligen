import typer
from typing_extensions import Annotated
from typing import Optional
import json
import os
import random

from engligen.core.crossword import Crossword
from engligen.rendering.image_renderer import ImageRenderer
from engligen.rendering.clue_generator import ClueGenerator

def load_default_paths():
    try:
        with open("data/config.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

default_paths = load_default_paths()
# Correção para Typer: Use add_completion=False para evitar comandos extras
app = typer.Typer(add_completion=False) 

@app.command()
def generate(
    themed_words_file: Annotated[str, typer.Option(
        "--arquivo-tema", "-t",
        help="Caminho para o arquivo .json com palavras e dicas do tema."
    )] = default_paths.get("themed_words_file"),
    common_words_file: Annotated[str, typer.Option(
        "--arquivo-curinga", "-c",
        help="Caminho para o arquivo .json com palavras e dicas comuns."
    )] = default_paths.get("common_words_file"),
    altura: Annotated[int, typer.Option(
        "--altura", "-h",
        help="Altura máxima da área de geração da grade (ex: 20)."
    )] = 20,
    largura: Annotated[int, typer.Option(
        "--largura", "-w",
        help="Largura máxima da área de geração da grade (ex: 15)."
    )] = 15,
    output_basename: Annotated[str, typer.Option(
        "--basename", "-b",
        help="Nome base para os arquivos de saída."
    )] = "exercicio",
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Semente para geração determinística."
    )] = None
):
    """Gera um exercício de palavras cruzadas em formato de imagem."""
    if not themed_words_file or not common_words_file:
        print("❌ ERRO: Arquivos de palavras não especificados e não encontrados no 'data/config.json'.")
        raise typer.Exit(code=1)

    if seed is not None:
        random.seed(seed)
        print(f"🎯 Seed configurada: {seed}")

    print("⚙️  Iniciando a geração do exercício...")
    print(f"📐 Dimensões da grade: {altura} linhas × {largura} colunas")

    try:
        with open(themed_words_file, 'r', encoding='utf-8') as f:
            themed_data = json.load(f)
        with open(common_words_file, 'r', encoding='utf-8') as f:
            common_data = json.load(f)
        
        all_words_data = themed_data + common_data
        words = [item['word'].upper() for item in all_words_data]
        clues_map = {item['word'].upper(): item['clue'] for item in all_words_data}

        print(f"✔️  Bancos de palavras carregados. Total de {len(words)} palavras disponíveis.")
    except Exception as e:
        print(f"❌ ERRO ao ler os arquivos JSON: {e}")
        raise typer.Exit(code=1)

    print("🧠  Buscando a melhor solução de grade com o algoritmo de ancoragem...")
    
    crossword_puzzle = Crossword(words, width=largura, height=altura)
    if not crossword_puzzle.generate():
        print("\n❌ FALHA: O algoritmo não conseguiu encontrar uma solução válida.")
        raise typer.Exit(code=1)

    print(f"✅ SUCESSO! Grade gerada com {len(crossword_puzzle.placed_words)} palavras.")

    total_cells = crossword_puzzle.width * crossword_puzzle.height
    if total_cells > 0:
        occupied_cells = sum(1 for row in crossword_puzzle.grid for cell in row if cell is not None)
        occupation_percentage = (occupied_cells / total_cells) * 100
        print("\n📊 Estatísticas da Grade:")
        print(f"   - Palavras Encaixadas: {len(crossword_puzzle.placed_words)}")
        print(f"   - Dimensões Finais: {crossword_puzzle.width}x{crossword_puzzle.height} ({total_cells} células)")
        print(f"   - Taxa de Ocupação: {occupation_percentage:.2f}%")

    print("\n📦 Gerando arquivos de saída...")

    clue_generator = ClueGenerator(crossword_puzzle, clues_map)
    
    # *** AQUI ESTÁ A CORREÇÃO ***
    # Chamando o método correto 'generate_text_file'
    clue_generator.generate_text_file(filename=f"{output_basename}_clues.txt")

    image_renderer = ImageRenderer(crossword_puzzle, clue_generator, cell_size=40, padding=25)
    image_renderer.generate_image(filename=f"{output_basename}_exercicio.png", answers=False, dpi=300)
    image_renderer.generate_image(filename=f"{output_basename}_respostas.png", answers=True, dpi=300)

    print(f"\n🎉 Tudo pronto! Verifique a pasta 'output'.")

# Adicionado para garantir que o script possa ser executado diretamente se necessário
def run():
    app()

if __name__ == "__main__":
    run()