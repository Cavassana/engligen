import typer
from typing_extensions import Annotated
from typing import Optional, List, Set, Dict
import json
import os
import random
from pathlib import Path

# O import do nosso novo Crossword
from engligen.core.crossword import Crossword
from engligen.rendering.image_renderer import ImageRenderer
from engligen.rendering.clue_generator import ClueGenerator

# --- Gestão de Palavras Usadas ---
def carregar_palavras_usadas(caminho_arquivo: Path) -> Set[str]:
    """Carrega o conjunto de palavras já utilizadas de um arquivo JSON."""
    if not caminho_arquivo.exists():
        return set()
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError):
        return set()

def salvar_palavras_usadas(caminho_arquivo: Path, palavras_novas: Set[str], palavras_antigas: Set[str]):
    """Adiciona novas palavras usadas à lista e salva no arquivo JSON."""
    palavras_atualizadas = palavras_antigas.union(palavras_novas)
    caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(palavras_atualizadas)), f, indent=4)
    print(f"✔️  Banco de palavras usadas atualizado com {len(palavras_novas)} novas palavras.")

def carregar_dados_palavras(caminho_arquivo: str) -> List[Dict]:
    """Carrega os dados de um arquivo JSON de palavras."""
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ ERRO ao ler o arquivo JSON '{caminho_arquivo}': {e}")
        raise typer.Exit(code=1)

def load_default_paths():
    """Carrega os caminhos padrão do arquivo de configuração."""
    try:
        with open("data/config.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

default_paths = load_default_paths()
app = typer.Typer(add_completion=False, help="Gerador de exercícios de palavras cruzadas para o Engligen.")

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
    output_basename: Annotated[str, typer.Option(
        "--basename", "-b",
        help="Nome base para os arquivos de saída."
    )] = "exercicio",
    seed: Annotated[Optional[int], typer.Option(
        "--seed",
        help="Semente para geração determinística."
    )] = None,
    altura: Annotated[int, typer.Option(
        "--altura", "-h",
        help="Altura máxima da grade de palavras."
    )] = 20,
    largura: Annotated[int, typer.Option(
        "--largura", "-w",
        help="Largura máxima da grade de palavras."
    )] = 15,
    reset: Annotated[bool, typer.Option(
        "--reset",
        help="Limpa o histórico de palavras usadas antes de gerar."
    )] = False
):
    """Gera um exercício de palavras cruzadas em formato de imagem."""
    project_root = Path(__file__).resolve().parents[2]
    caminho_palavras_usadas = project_root / "data" / "wordlists" / "used_words.json"

    if reset:
        if caminho_palavras_usadas.exists():
            caminho_palavras_usadas.unlink()
            print("🗑️  Histórico de palavras usadas foi limpo.")
        else:
            print("ℹ️  Nenhum histórico de palavras usadas para limpar.")

    if not themed_words_file or not common_words_file:
        print("❌ ERRO: Arquivos de palavras não especificados e não encontrados no 'data/config.json'.")
        raise typer.Exit(code=1)

    if seed is not None:
        random.seed(seed)
        print(f"🎯 Seed configurada: {seed}")

    print("⚙️  Iniciando a geração do exercício...")

    # --- LÓGICA DE CARREGAMENTO E FILTRAGEM CORRIGIDA ---
    themed_data = carregar_dados_palavras(themed_words_file)
    common_data = carregar_dados_palavras(common_words_file)
    
    palavras_usadas = carregar_palavras_usadas(caminho_palavras_usadas)
    print(f"📖 Carregadas {len(palavras_usadas)} palavras do histórico de uso.")

    # Cria conjuntos com todas as palavras originais para referência
    original_themed_set = {item['word'].upper() for item in themed_data}
    original_common_set = {item['word'].upper() for item in common_data}
    
    # Cria as listas de palavras disponíveis para o gerador
    themed_list_disponivel = list(original_themed_set - palavras_usadas)
    common_list_disponivel = list(original_common_set - palavras_usadas)
    
    # Cria o mapa de dicas para a renderização
    all_words_data = themed_data + common_data
    clues_map = {item['word'].upper(): item['clue'] for item in all_words_data}

    print(f"✔️  Bancos de palavras carregados. {len(themed_list_disponivel)}/{len(original_themed_set)} palavras temáticas e {len(common_list_disponivel)}/{len(original_common_set)} curingas disponíveis.")
    
    if not themed_list_disponivel:
        print("❌ ERRO: Não há palavras temáticas disponíveis para gerar o exercício.")
        raise typer.Exit(code=1)

    print("🧠  Buscando a melhor solução de grade...")
    
    crossword_puzzle = Crossword(
        themed_words=themed_list_disponivel, 
        common_words=common_list_disponivel,
        max_size=(altura, largura)
    )
    
    if not crossword_puzzle.generate():
        print("\n❌ FALHA: O algoritmo não conseguiu encontrar uma solução válida após múltiplas tentativas.")
        raise typer.Exit(code=1)

    print(f"✅ SUCESSO! Melhor grade encontrada com {len(crossword_puzzle.placed_words)} palavras.")
    
    # --- RELATÓRIO DE DISTRIBUIÇÃO CORRIGIDO ---
    palavras_colocadas = set(crossword_puzzle.placed_words.keys())
    tematicas_usadas_final = palavras_colocadas.intersection(original_themed_set)
    comuns_usadas_final = palavras_colocadas.intersection(original_common_set)

    total_cells = crossword_puzzle.width * crossword_puzzle.height
    if total_cells > 0:
        occupied_cells = sum(1 for row in crossword_puzzle.grid for cell in row if cell is not None)
        occupation_percentage = (occupied_cells / total_cells) * 100
        print("\n📊 Estatísticas da Grade:")
        print(f"   - Palavras Encaixadas: {len(palavras_colocadas)} (Temáticas: {len(tematicas_usadas_final)}, Comuns: {len(comuns_usadas_final)})")
        print(f"   - Dimensões Finais: {crossword_puzzle.width}x{crossword_puzzle.height} ({total_cells} células)")
        print(f"   - Taxa de Ocupação: {occupation_percentage:.2f}%")

    print("\n📦 Gerando arquivos de saída...")
    
    # --- ATUALIZAÇÃO DO HISTÓRICO DE PALAVRAS ---
    salvar_palavras_usadas(caminho_palavras_usadas, palavras_colocadas, palavras_usadas)

    clue_generator = ClueGenerator(crossword_puzzle, clues_map)
    clue_generator.generate_text_file(filename=f"{output_basename}_clues.txt")

    image_renderer = ImageRenderer(crossword_puzzle, clue_generator, cell_size=40, padding=25)
    image_renderer.generate_image(filename=f"{output_basename}_exercicio.png", answers=False, dpi=300)
    image_renderer.generate_image(filename=f"{output_basename}_respostas.png", answers=True, dpi=300)

    print(f"\n🎉 Tudo pronto! Verifique a pasta 'output'.")

def run():
    app()

if __name__ == "__main__":
    run()
