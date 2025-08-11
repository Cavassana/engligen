# Engligen — Gerador de Exercícios (Crossword & WordSearch)

> Ferramenta CLI para criar **palavras‑cruzadas** e **caça‑palavras** a partir de bancos de palavras em JSON. Foco em impressão econômica (ink‑saver), experiência de professor e reuso ao longo de unidades temáticas.

---

## Sumário

* [Requisitos](#requisitos)
* [Instalação (modo editável)](#instalação-modo-editável)
* [Como executar](#como-executar)
* [Estrutura do projeto](#estrutura-do-projeto)
* [Formato dos bancos de palavras (JSON)](#formato-dos-bancos-de-palavras-json)
* [Fluxos de seleção dos JSONs](#fluxos-de-seleção-dos-jsons)

  * [Autodetecção em `data/wordlists/` (recomendado)](#autodetecção-em-datawordlists-recomendado)
  * [Informar caminhos manualmente (só nesta execução)](#informar-caminhos-manualmente-só-nesta-execução)
  * [Persistente via `config.json` (fica salvo)](#persistente-via-configjson-fica-salvo)
* [Gerando exercícios](#gerando-exercícios)

  * [Crossword (palavras‑cruzadas)](#crossword-palavrascruzadas)
  * [WordSearch (caça‑palavras)](#wordsearch-caça-palavras)
* [Saídas geradas](#saídas-geradas)
* [Preferências de impressão (ink‑saver)](#preferências-de-impressão-ink-saver)
* [Histórico de uso de palavras](#histórico-de-uso-de-palavras)
* [Unidades do curso (wizard)](#unidades-do-curso-wizard)
* [Configuração (`data/config.json`)](#configuração-dataconfigjson)
* [Solução de problemas](#solução-de-problemas)
* [Roadmap](#roadmap)

---

## Requisitos

* **Python 3.10+** (testado no Windows 10/11; deve funcionar em Linux/macOS)
* Pip atualizada

## Instalação (modo editável)

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .

# Verifique o comando
where engligen  # deve apontar para .venv\Scripts\engligen.exe
```

No Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
which engligen
```

## Como executar

```bash
engligen
```

Você verá um menu com:

```
1) Gerar Palavra-Cruzada (Crossword)
2) Gerar Caça-Palavras (WordSearch)
3) Iniciar NOVA UNIDADE (assistente)
4) Sair
```

## Estrutura do projeto

```
engligen/
├─ data/
│  ├─ wordlists/                 # coloque aqui seus .json de palavras
│  │  ├─ general_words.json      # exemplo (coringa)
│  │  ├─ unit01_thematic_words.json  # exemplo (temático)
│  │  ├─ used_common.json        # histórico (auto)
│  │  └─ used_thematic.json      # histórico (auto)
│  └─ config.json                # perfil ativo (auto/edição manual)
├─ output/                       # imagens e dicas geradas
├─ src/engligen/
│  ├─ app.py
│  ├─ ui/menu.py
│  ├─ core/
│  └─ rendering/
└─ pyproject.toml
```

## Formato dos bancos de palavras (JSON)

Arquivo JSON com **lista de objetos**. Cada objeto tem:

* `word`: **A–Z apenas**, sem espaços/acentos (use *UPPERCASE*)
* `clue`: texto da dica (qualquer string)

Exemplo mínimo:

```json
[
  {"word": "ADAMSMITH", "clue": "Autor de The Wealth of Nations."},
  {"word": "MERCANTILISM", "clue": "Doutrina econômica dos metais preciosos."}
]
```

> Observação: o gerador não normaliza acentos/espaços. Garanta que `word` está limpo e em maiúsculas.

## Fluxos de seleção dos JSONs

### Autodetecção em `data/wordlists/` (recomendado)

Ao gerar **Crossword** ou **WordSearch**, o sistema pergunta:

> "Tentar DETECTAR automaticamente os arquivos em `data/wordlists/`?"

Se **Sim**:

1. Lista os `.json` candidatos (ignora `used_*.json` e `config*`).
2. Mostra contagem de itens válidos por arquivo e **sugere papel** (`common`/`themed`) por heurística de nome.
3. Se identificar uma dupla plausível, pergunta se quer usar (Coringa vs Temático). Senão, você escolhe pelo número.

### Informar caminhos manualmente (só nesta execução)

Recuse a autodetecção ou escolha a opção **m** quando não houver candidatos. Você informa:

* Caminho do **coringa** (`.json`) — opcional (deixe vazio para usar o da config)
* Um ou mais **temáticos**, separados por `;`

### Persistente via `config.json` (fica salvo)

Se preferir, defina caminhos fixos em `data/config.json`:

```json
{
  "common_words_file": "data/wordlists/general_words.json",
  "course": {
    "include_previous_units": true,
    "active_unit": "u1",
    "units": [
      {"slug": "u1", "name": "Unit 1 — Adam Smith", "themed_words_file": "data/wordlists/unit01_thematic_words.json"}
    ]
  }
}
```

## Gerando exercícios

### Crossword (palavras‑cruzadas)

Fluxo típico:

1. Informe **nome‑base** (ex.: `u1_cw01`).
2. Altura/Largura, **seed** (opcional, para reprodutibilidade).
3. Autodetecção/seleção de bancos (ver seção anterior).
4. Preferências: **ink‑saver** (recomendado), **header** (título opcional).
5. **Prefill por palavras inteiras**: escolha quantas palavras completas revelar (prioriza as temáticas da unidade).

Características do renderizador (ink‑saver):

* **Fundo branco liso**.
* **Blocos (células pretas)** são **hachurados diagonalmente** (sem preenchimento sólido) para economizar tinta.
* Numeração compacta; setas **→**/**↓** posicionadas sem sobrepor os números.
* `watermark` **desativada** por padrão (só aplica se configurada).

### WordSearch (caça‑palavras)

Fluxo típico:

1. Informe **nome‑base** (ex.: `u1_ws01`) e **tamanho** (NxN).
2. Autodetecção/seleção de bancos.
3. Se **palavras temáticas restantes** estiverem esgotadas, o sistema oferece **complementar com o banco coringa** (opção recomendada).

> Nota: o WordSearch **respeita** `used_thematic.json` (não usa palavras já consumidas nas cruzadas), mas **não marca** novos usos no histórico (planejamos tornar isso configurável).

## Saídas geradas

Na pasta `output/`:

* `*_exercicio.png` — folha do aluno (letras ocultas, com prefill opcional)
* `*_respostas.png` — gabarito
* `*_clues.txt` — lista numerada de dicas

Imagens são salvas com **300 DPI**. Formato PNG.

## Preferências de impressão (ink‑saver)

* Fundo **branco**.
* **Blocos hachurados** (parâmetros internos atuais: `spacing=6`, `thickness=1`).
* Linhas **cinza escuro** e texto **preto**.

> Ajustes finos de hachura serão expostos em `config.json` em versões futuras.

## Histórico de uso de palavras

Arquivos mantidos em `data/wordlists/`:

* `used_thematic.json` — acumula palavras **temáticas** já usadas nas cruzadas (evita repetir).
* `used_common.json` — idem para **coringa**.

Compatibilidade com legado:

* Se existir `used_words.json` antigo e os arquivos novos não existirem, o sistema migra automaticamente.

## Unidades do curso (wizard)

Opção **3) Iniciar NOVA UNIDADE**:

* Define `slug`, nome e **arquivo temático** da unidade.
* Define se a unidade deve **incluir conteúdo de unidades anteriores**.
* Permite ajustar **header** e preferências de **prefill padrão** (opcional).
* Salva um perfil `data/config_<slug>.json` e o ativa como `data/config.json`.

> Você também pode ignorar o wizard e usar apenas a **autodetecção**/seleção manual dos bancos no momento de gerar cada exercício.

## Configuração (`data/config.json`)

Chaves relevantes (todas opcionais):

```json
{
  "common_words_file": "data/wordlists/general_words.json",
  "themed_words_file": "data/wordlists/unit01_thematic_words.json",   // legado (quando não usar "course")
  "course": {
    "include_previous_units": true,
    "active_unit": "u1",
    "units": [
      {"slug": "u1", "name": "Unit 1", "themed_words_file": "data/wordlists/unit01_thematic_words.json"}
    ]
  },
  "renderer": {
    "ink_saver": true,
    "header_text": "Crossword – Unit 1",
    "watermark_text": null,
    "prefill": { "mode": null }  // "first" ou "percent" se quiser um padrão global
  },
  "used_words": {  // caminhos dos históricos
    "common_file": "data/wordlists/used_common.json",
    "themed_file": "data/wordlists/used_thematic.json"
  }
}
```

## Solução de problemas

**O comando `engligen` não é encontrado**

* Garanta instalação em modo editável: `python -m pip install -e .`
* Ative o venv. No Windows, `where engligen` deve apontar para `.venv\Scripts\engligen.exe`.

**Erro de fonte (Arial)**

* O renderer cai em **fonte padrão** se `arial.ttf` não estiver disponível. Para consistência, instale Arial no sistema ou troque por outra TTF no código, se necessário.

**"Sem palavras temáticas restantes" no WordSearch**

* Responda **Sim** para completar com o **banco coringa**.
* Se não quiser completar, adicione mais itens ao temático da unidade.

**Pylance reclamando de indentação/`return` fora de função**

* Certifique-se de que está com os arquivos `app.py`, `menu.py` e renderizadores mais recentes e reinstale com `-e`.

## Roadmap

* Expor parâmetros de hachura dos blocos em `config.json`.
* Registrar (opcional) uso de palavras também no WordSearch.
* Exportação direta para PDF.
* Geração automática de bancos via IA (ainda não implementado).

---

> Dúvidas ou sugestões: abra uma *issue* no repositório e anexe trechos de console e imagens de saída para facilitar a reprodução.
