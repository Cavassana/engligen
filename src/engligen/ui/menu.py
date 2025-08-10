from typing import Optional
from engligen.app import EngligenApp

class Menu:
    """
    Gerencia a interface de linha de comando (menu) para o usuário.
    """
    def __init__(self):
        self.app = EngligenApp()

    def _exibir_menu(self):
        """Mostra as opções disponíveis para o usuário."""
        print("\n╔═════════════════════════════════════╗")
        print("║   Engligen: Gerador de Exercícios   ║")
        print("╠═════════════════════════════════════╣")
        print("║ 1. Gerar Palavras Cruzadas          ║")
        print("║ 2. Gerar Caça-Palavras              ║")
        print("║ 3. Sair                             ║")
        print("╚═════════════════════════════════════╝")

    def _get_input_crossword(self):
        """Coleta as informações necessárias para as palavras cruzadas."""
        print("\n--- Gerador de Palavras Cruzadas ---")
        output_basename = input("▶ Insira o nome base para os arquivos (ex: exercicio_01): ")
        altura = int(input("▶ Insira a altura máxima da grade (padrão: 20): ") or "20")
        largura = int(input("▶ Insira a largura máxima da grade (padrão: 15): ") or "15")
        seed_input = input("▶ Insira uma semente (seed) para resultados consistentes (opcional): ")
        reset_input = input("▶ Limpar histórico de palavras usadas? (s/n): ").lower()
        
        seed: Optional[int] = int(seed_input) if seed_input.isdigit() else None
        reset: bool = reset_input == 's'
        
        self.app.executar_gerador_crossword(output_basename, altura, largura, seed, reset)

    def _get_input_wordsearch(self):
        """Coleta as informações necessárias para o caça-palavras."""
        print("\n--- Gerador de Caça-Palavras ---")
        output_basename = input("▶ Insira o nome base para os arquivos (ex: caca_palavras_01): ")
        size = int(input("▶ Insira o tamanho da grelha (padrão: 15): ") or "15")

        self.app.executar_gerador_wordsearch(output_basename, size)

    def run(self):
        """Inicia o loop principal do menu."""
        while True:
            self._exibir_menu()
            escolha = input("Escolha uma opção: ")

            if escolha == '1':
                self._get_input_crossword()
            elif escolha == '2':
                self._get_input_wordsearch()
            elif escolha == '3':
                print("\nSaindo do programa. Até mais!")
                break
            else:
                print("\nOpção inválida. Por favor, tente novamente.")