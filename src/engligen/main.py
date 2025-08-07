# src/engligen/main.py

import typer
from typing_extensions import Annotated
import json
import os

from engligen.core.crossword import Crossword
from engligen.rendering.image_renderer import ImageRenderer
from engligen.rendering.clue_generator import ClueGenerator

# Função para carregar os caminhos padrão do config.json
def load_default_paths():
    try:
        with open("data/config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        return {}

default_paths = load_default_paths()

app = typer.Typer()

@app.command()
def generate(
    themed_words_file: Annotated[str, typer.Option("--arquivo-tema", "-t", help="Caminho para o arquivo .json com palavras e dicas do tema.")] = default_paths.get("themed_words_file"),
    common_words_file: Annotated[str, typer.Option("--arquivo-curinga", "-c", help="Caminho para o arquivo .json com palavras e dicas comuns.")] = default_paths.get("common_words_file"),
    altura: Annotated[int, typer.Option("--altura", "-h", help="Altura máxima da área de geração da grade (ex: 20).")] = 20,
    largura: Annotated[int, typer.Option("--largura", "-w", help="Largura máxima da área de geração da grade (ex: 15).")] = 15,
    output_basename: Annotated[str, typer.Option("--basename", "-b", help="Nome base para os arquivos de saída.")] = "exercicio"
):
    """
    Gera uma grade de palavras-cruzadas otimizada usando um algoritmo de ancoragem.
    PADRÃO: 20 linhas x 15 colunas
    """
    if not themed_words_file or not common_words_file:
        print("❌ ERRO: Arquivos de palavras não especificados e não encontrados no 'data/config.json'.")
        raise typer.Exit(code=1)

    print("⚙️  Iniciando a geração do exercício...")
    print(f"📐 Dimensões da grade: {altura} linhas × {largura} colunas")

    # --- 1. Carregar e combinar os dois bancos de palavras ---
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

    # --- 2. Gerar a grade com o algoritmo otimizado ---
    print("🧠  Buscando a melhor solução de grade com o algoritmo de ancoragem...")
    
    # Garantir que largura seja passada como width e altura como height
    crossword_puzzle = Crossword(words, width=largura, height=altura)
    is_successful = crossword_puzzle.generate()
    
    # --- 3. Gerar Arquivos de Saída ---
    if not is_successful or not crossword_puzzle.placed_words:
        print("\n❌ FALHA: O algoritmo não conseguiu encontrar uma solução válida com as palavras e restrições fornecidas.")
        raise typer.Exit(code=1)

    print(f"✅ SUCESSO! Grade gerada com {len(crossword_puzzle.placed_words)} palavras.")

    # --- Bloco de Logs e Estatísticas ---
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
    
    # Tamanho da célula menor para grade mais compacta 15x20
    image_renderer = ImageRenderer(crossword_puzzle, clue_generator, cell_size=40, padding=25)
    #image_renderer = ImageRenderer(crossword_puzzle, clue_generator, cell_size=28, padding=20)
    
    # DEPOIS (com alta resolução)
    image_renderer.generate_image(
        filename=f"{output_basename}_exercicio.png",
        include_answers=False,
        dpi=300
    )
    image_renderer.generate_image(
        filename=f"{output_basename}_respostas.png",
        include_answers=True,
        dpi=300
    )
    print(f"\n🎉 Tudo pronto! Verifique a pasta 'output'.")

def run():
    app()

if __name__ == "__main__":
    run()