# Engligen - Gerador de Exercícios de Inglês

Este projeto é uma ferramenta de linha de comando (CLI) para gerar automaticamente exercícios de **Palavras Cruzadas** e **Caça-Palavras** a partir de listas de palavras. Para cada exercício, ele cria imagens de alta resolução da grelha (com e sem respostas) e um arquivo de texto com as dicas.

## Funcionalidades Principais

* **Dois Tipos de Exercícios**: Geração de Palavras Cruzadas e Caça-Palavras.
* **Geração Inteligente**: O algoritmo de palavras cruzadas busca a melhor disposição para as palavras, maximizando o número de intersecções.
* **Interface Interativa**: Um menu de fácil utilização guia o usuário na escolha e configuração do exercício desejado.
* **Controle de Palavras Usadas**: Mantém um histórico (`used_words.json`) para garantir que os exercícios de palavras cruzadas sejam sempre novos.
* **Saída Pronta para Uso**: Gera arquivos `.png` de alta resolução para o exercício e para as respostas, ideais para impressão ou uso digital, além de um `.txt` com as pistas.
* **Configuração Flexível**: Permite definir facilmente quais arquivos de palavras serão usados através do arquivo `data/config.json`.

## Como Rodar o Projeto

Certifique-se de que você tem um ambiente virtual Python ativado.

### 1. Instalar o Projeto

Este comando instala o projeto e suas dependências (como a biblioteca `Pillow`) e cria o comando `engligen` no seu terminal.

```bash
pip install -e .

2. Executar o Gerador

Para iniciar a aplicação e acessar o menu interativo, execute o seguinte comando no seu terminal:
Bash

engligen

3. Usar o Menu Interativo

Após executar o comando, um menu será exibido:

╔═════════════════════════════════════╗
║   Engligen: Gerador de Exercícios   ║
╠═════════════════════════════════════╣
║ 1. Gerar Palavras Cruzadas          ║
║ 2. Gerar Caça-Palavras              ║
║ 3. Sair                             ║
╚═════════════════════════════════════╝

    Para Palavras Cruzadas: Escolha a opção 1 e siga as instruções para definir o nome base dos arquivos, as dimensões da grelha e outras configurações.

    Para Caça-Palavras: Escolha a opção 2 e informe o nome base e o tamanho desejado para a grelha.

Todos os arquivos de saída (imagens e pistas) serão salvos na pasta output/.

Estrutura dos Arquivos de Saída

Ao gerar um exercício com o nome base exercicio_01, por exemplo, os seguintes arquivos serão criados na pasta output/:

    exercicio_01_exercicio.png: A grelha vazia para resolver.

    exercicio_01_respostas.png: A grelha com as respostas preenchidas.

    exercicio_01_clues.txt: A lista de dicas numeradas (apenas para palavras cruzadas).

    exercicio_01_list.txt: A lista de palavras a serem encontradas (apenas para caça-palavras).