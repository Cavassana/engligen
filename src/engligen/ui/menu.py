
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

from engligen.app import EngligenApp


# -------------------- Helpers --------------------

def _ask_bool(prompt: str, default: bool = True) -> bool:
    """Pergunta s/n (Enter usa default)."""
    default_txt = "Sim" if default else "Não"
    while True:
        s = input(f"{prompt} [Enter={default_txt} | s/n]: ").strip().lower()
        if s == "":
            return default
        if s in {"s", "sim", "y", "yes"}:
            return True
        if s in {"n", "nao", "não", "no"}:
            return False
        print("Resposta inválida. Digite s/n ou Enter para manter o padrão.")


def _ask_then_confirm_str(prompt: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    """1) pergunta; 2) confirma; 3) se 'não', repete."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        s = input(f"{prompt}{suffix}: ").strip()
        if s == "":
            if default is None and not allow_empty:
                print("Valor não pode ser vazio.")
                continue
            value = "" if default is None else default
        else:
            value = s
        if _ask_bool(f"Confirma o valor: '{value}'?", default=True):
            return value


def _ask_then_confirm_float(prompt: str, default: float, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float:
    while True:
        s = input(f"{prompt} [{default}]: ").strip()
        if s == "":
            v = float(default)
        else:
            try:
                v = float(s)
            except ValueError:
                print("Valor inválido. Digite um número.")
                continue
        if min_value is not None and v < min_value:
            print(f"Valor mínimo: {min_value}")
            continue
        if max_value is not None and v > max_value:
            print(f"Valor máximo: {max_value}")
            continue
        if _ask_bool(f"Confirma o valor: {v}?", default=True):
            return v


# --------- Descoberta automática de arquivos (.json) ---------

_SKIP_PATTERNS = ("used_common.json", "used_thematic.json", "used_words.json", "config", "_clues.txt")

def _default_wordlist_dir(project_root: Path) -> Path:
    return (project_root / "data" / "wordlists").resolve()

def _is_candidate_json(p: Path) -> bool:
    name = p.name.lower()
    if not p.suffix.lower() == ".json":
        return False
    if any(k in name for k in _SKIP_PATTERNS):
        return False
    return True

def _validate_wordlist_file(path: Path) -> Tuple[int, int]:
    """
    Retorna (validos, total). Considera válido item que possua 'word' str não-vazia.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return (0, 0)
        total = len(data)
        valid = 0
        for it in data:
            if isinstance(it, dict) and isinstance(it.get("word"), str) and it.get("word").strip():
                valid += 1
        return (valid, total)
    except Exception:
        return (0, 0)

def _guess_role(name: str) -> Optional[str]:
    n = name.lower()
    if any(k in n for k in ["common", "general", "coringa", "geral"]):
        return "common"
    if any(k in n for k in ["thematic", "tema", "tematico", "temático", "unit", "unidade", "u0", "u1", "u2", "u3", "u4", "u5", "u6", "u7", "u8", "u9"]):
        return "themed"
    return None

def _auto_detect_wordlists(project_root: Path) -> Tuple[Optional[str], Optional[List[str]]]:
    """
    Escaneia a pasta padrão e sugere arquivos para coringa/temático.
    Retorna (common_path, themed_paths) ou (None, None) se nada decidido.
    """
    folder = _default_wordlist_dir(project_root)
    if not folder.exists():
        return (None, None)

    candidates = [p for p in folder.iterdir() if _is_candidate_json(p)]
    # Ordena por heurística de "recentes" (modificado por último)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if not candidates:
        print("ℹ️  Nenhum .json candidato encontrado em data/wordlists.")
        return (None, None)

    # Mostra candidatos com contagem
    print("\nArquivos encontrados em data/wordlists:")
    info = []
    for i, p in enumerate(candidates, 1):
        valid, total = _validate_wordlist_file(p)
        role = _guess_role(p.name) or "?"
        print(f"  {i:>2}) {p.name}  — itens: {valid}/{total}  — sugestão: {role}")
        info.append((p, valid, total, role))

    # Tenta escolher automaticamente se houver 2 com papéis claros
    commons = [p for (p, _, _, role) in info if role == "common"]
    themeds = [p for (p, _, _, role) in info if role == "themed"]
    if len(commons) == 1 and len(themeds) == 1:
        print(f"Proposta: CORINGA = {commons[0].name} ; TEMÁTICO = {themeds[0].name}")
        if _ask_bool("Usar essa combinação?", default=True):
            return (str(commons[0]), [str(themeds[0])])

    # Caso geral: deixar o usuário escolher
    idx_common = _ask_then_confirm_str("Escolha o número do arquivo CORINGA (ex: 1)", default="1")
    try:
        i_common = int(idx_common)
        common_path = str(candidates[i_common - 1])
    except Exception:
        print("Seleção inválida para CORINGA.")
        return (None, None)

    idx_themed = _ask_then_confirm_str("Escolha o número do arquivo TEMÁTICO (ex: 2)", default="2")
    try:
        i_themed = int(idx_themed)
        themed_path = str(candidates[i_themed - 1])
    except Exception:
        print("Seleção inválida para TEMÁTICO.")
        return (None, None)

    if i_common == i_themed:
        print("Os arquivos CORINGA e TEMÁTICO não podem ser o mesmo.")
        return (None, None)

    return (common_path, [themed_path])


# -------------------- Menu --------------------

class Menu:
    """
    CLI do Engligen.
    - Geração de Crossword / WordSearch
    - Wizard de NOVA UNIDADE (cria config_uN.json e ativa)
    """
    def __init__(self) -> None:
        self.app = EngligenApp()
        self.project_root = self.app.project_root

    def _exibir_menu(self) -> None:
        print("\n╔═════════════════════════════════════╗")
        print("║   Engligen: Gerador de Exercícios   ║")
        print("╠═════════════════════════════════════╣")
        print("║ 1) Gerar Palavra-Cruzada (Crossword)║")
        print("║ 2) Gerar Caça-Palavras (WordSearch) ║")
        print("║ 3) Iniciar NOVA UNIDADE (assistente)║")
        print("║ 4) Sair                             ║")
        print("╚═════════════════════════════════════╝")

    def run(self) -> None:
        while True:
            self._exibir_menu()
            escolha = input("Escolha uma opção: ").strip()
            if escolha == "1":
                self._get_input_crossword()
            elif escolha == "2":
                self._get_input_wordsearch()
            elif escolha == "3":
                self._wizard_nova_unidade()
            elif escolha == "4":
                print("\nSaindo. Até mais!")
                break
            else:
                print("\nOpção inválida. Tente novamente.")

    # -------- Opção 1: Crossword --------

    def _get_input_crossword(self) -> None:
        print("\n▶ Gerar Palavra-Cruzada")
        basename = _ask_then_confirm_str("Insira o nome-base do arquivo (ex: cw_01_unit_01)", default="teste")
        altura = int(_ask_then_confirm_float("Altura (linhas)", default=20, min_value=5))
        largura = int(_ask_then_confirm_float("Largura (colunas)", default=15, min_value=5))
        seed_str = _ask_then_confirm_str("Seed (vazio = aleatória)", default="", allow_empty=True)
        seed = int(seed_str) if seed_str else None

        # Descoberta automática
        common_override = None
        themed_override_list: Optional[List[str]] = None
        if _ask_bool("Tentar DETECTAR automaticamente os arquivos em data/wordlists?", default=True):
            common_path, themed_paths = _auto_detect_wordlists(self.project_root)
            if common_path and themed_paths:
                common_override = common_path
                themed_override_list = themed_paths
            else:
                # Nenhuma detecção válida -> perguntar o que fazer
                print("\nNenhuma combinação confirmada.")
                print("Opções: (m) inserir caminhos manualmente | (a) gerar automaticamente (IA) | (c) cancelar")
                choice = input("Escolha [m/a/c]: ").strip().lower()
                if choice == "a":
                    print("⚠️  Ainda não implementado: geração automática com IA.")
                    print("Por favor, informe os caminhos manualmente.")
                    choice = "m"
                if choice == "c":
                    print("Operação cancelada.")
                    return
                if choice == "m":
                    co = _ask_then_confirm_str("Caminho do CORINGA (.json) [vazio = config]", default="", allow_empty=True)
                    common_override = co if co else None
                    to = _ask_then_confirm_str("Caminhos TEMÁTICOS (.json), separados por ';'", default="", allow_empty=True)
                    themed_override_list = [p.strip() for p in to.split(';') if p.strip()] if to else None
        else:
            # Fluxo antigo: perguntar se quer arquivos personalizados
            use_custom = _ask_bool("Usar ARQUIVOS personalizados nesta geração?", default=False)
            if use_custom:
                co = _ask_then_confirm_str("Caminho do CORINGA (.json) [vazio = config]", default="", allow_empty=True)
                common_override = co if co else None
                to = _ask_then_confirm_str("Caminhos TEMÁTICOS (.json), separados por ';'", default="", allow_empty=True)
                themed_override_list = [p.strip() for p in to.split(';') if p.strip()] if to else None

        # Overrides visuais
        ink = _ask_bool("Usar modo ink-saver (fundo branco)?", default=True)
        header = _ask_then_confirm_str("Header (vazio = usar config)", default="", allow_empty=True)
        header = header if header else None

        # Prefill por PALAVRAS
        n_words = int(_ask_then_confirm_float("Quantas PALAVRAS completas deseja exibir? [0 = nenhuma]", default=0, min_value=0))
        prefer_thematic = _ask_bool("Preferir palavras do banco TEMÁTICO ao escolher as exibidas?", default=True) if n_words > 0 else True

        ok = self.app.executar_gerador_crossword(
            output_basename=basename,
            altura=altura,
            largura=largura,
            seed=seed,
            reset=False,
            ink_saver=ink,
            header_text=header,
            prefill_words_count=int(n_words),
            prefill_prefer_thematic=bool(prefer_thematic),
            common_file_override=common_override,
            themed_files_override=themed_override_list,
        )
        if not ok:
            print("✖ Operação não concluída. Veja mensagens acima.")

    # -------- Opção 2: WordSearch --------

    def _get_input_wordsearch(self) -> None:
        print("\n▶ Gerar Caça-Palavras")
        basename = _ask_then_confirm_str("Insira o nome-base do arquivo (ex: ws_01_unit_01)", default="wordsearch")
        size = int(_ask_then_confirm_float("Tamanho da grade (NxN)", default=15, min_value=5))

        # Descoberta automática
        common_override = None
        themed_override_list: Optional[List[str]] = None
        if _ask_bool("Tentar DETECTAR automaticamente os arquivos em data/wordlists?", default=True):
            common_path, themed_paths = _auto_detect_wordlists(self.project_root)
            if common_path and themed_paths:
                common_override = common_path
                themed_override_list = themed_paths
            else:
                print("\nNenhuma combinação confirmada.")
                print("Opções: (m) inserir caminhos manualmente | (a) gerar automaticamente (IA) | (c) cancelar")
                choice = input("Escolha [m/a/c]: ").strip().lower()
                if choice == "a":
                    print("⚠️  Ainda não implementado: geração automática com IA.")
                    print("Por favor, informe os caminhos manualmente.")
                    choice = "m"
                if choice == "c":
                    print("Operação cancelada.")
                    return
                if choice == "m":
                    co = _ask_then_confirm_str("Caminho do CORINGA (.json) [vazio = config]", default="", allow_empty=True)
                    common_override = co if co else None
                    to = _ask_then_confirm_str("Caminhos TEMÁTICOS (.json), separados por ';'", default="", allow_empty=True)
                    themed_override_list = [p.strip() for p in to.split(';') if p.strip()] if to else None
        else:
            use_custom = _ask_bool("Usar ARQUIVOS personalizados nesta geração?", default=False)
            if use_custom:
                co = _ask_then_confirm_str("Caminho do CORINGA (.json) [vazio = config]", default="", allow_empty=True)
                common_override = co if co else None
                to = _ask_then_confirm_str("Caminhos TEMÁTICOS (.json), separados por ';'", default="", allow_empty=True)
                themed_override_list = [p.strip() for p in to.split(';') if p.strip()] if to else None

        use_fallback = _ask_bool("Se esgotar temáticas, completar com banco coringa?", default=True)

        ok = self.app.executar_gerador_wordsearch(
            output_basename=basename,
            size=size,
            allow_fallback_common=use_fallback,
            common_file_override=common_override,
            themed_files_override=themed_override_list,
        )
        if not ok:
            print("✖ Operação não concluída. Veja mensagens acima.")

    # -------- Opção 3: Wizard Nova Unidade --------

    def _wizard_nova_unidade(self) -> None:
        print("\n▶ Assistente: Iniciar NOVA UNIDADE")
        cfg: Dict[str, Any] = self.app.config or {}
        course = cfg.get("course") or {}
        units = course.get("units") or []
        if not course:
            course = {"include_previous_units": True, "units": []}
            cfg["course"] = course

        include_prev_default = bool(course.get("include_previous_units", True))

        next_index = len(units) + 1
        default_slug = f"u{next_index}"
        default_name = f"Unit {next_index} – <tema>"
        default_file = f"data/wordlists/unidade_{next_index}_word_bank.json"

        print("\nVamos configurar a nova unidade. Primeiro você informa o valor, depois confirma.")

        slug = _ask_then_confirm_str("Slug da unidade", default=default_slug)
        name = _ask_then_confirm_str("Nome/título da unidade", default=default_name)
        themed_file = _ask_then_confirm_str("Arquivo temático (JSON)", default=default_file)

        include_prev = _ask_bool("Incluir conteúdo das unidades anteriores nesta unidade?", default=include_prev_default)

        header_sug = f"Crossword – {name}"
        header_text = _ask_then_confirm_str("Header (título no topo)", default=header_sug)
        watermark_text = _ask_then_confirm_str("Watermark (vazio = nenhuma)", default="", allow_empty=True)
        watermark_text = watermark_text if watermark_text else None

        print("\nPrefill padrão (salvo no config; pode ser sobrescrito na geração):")
        use_first = _ask_bool("Usar prefill 'first' (1ª letra)?", default=False)
        prefill_cfg: Dict[str, Any] = {}
        if use_first:
            inc_across = _ask_bool("Prefill Across?", default=True)
            inc_down = _ask_bool("Prefill Down?", default=False)
            prefill_cfg = {"mode": "first", "include_across": inc_across, "include_down": inc_down}
        else:
            prefill_cfg = {"mode": None}

        print("\nResumo da nova unidade:")
        print(f"  • slug            : {slug}")
        print(f"  • name            : {name}")
        print(f"  • themed file     : {themed_file}")
        print(f"  • include_prev    : {include_prev}")
        print(f"  • header          : {header_text}")
        print(f"  • watermark       : {watermark_text}")
        print(f"  • prefill         : {prefill_cfg}")
        if not _ask_bool("Confirma criação/ativação desta unidade?", default=True):
            print("Operação cancelada.")
            return

        new_unit = {"slug": slug, "name": name, "themed_words_file": themed_file}
        units.append(new_unit)
        course["units"] = units
        course["include_previous_units"] = include_prev
        course["active_unit"] = slug
        cfg["course"] = course

        renderer = cfg.get("renderer") or {}
        renderer["ink_saver"] = True if renderer.get("ink_saver") is None else bool(renderer.get("ink_saver"))
        renderer["header_text"] = header_text
        renderer["watermark_text"] = watermark_text
        renderer.setdefault("arrow_gap_px", 2)
        renderer.setdefault("corner_pad", 2)
        renderer["background_style"] = renderer.get("background_style", "plain")
        renderer["prefill"] = prefill_cfg
        cfg["renderer"] = renderer

        cfg_dir = self.project_root / "data"
        cfg_dir.mkdir(parents=True, exist_ok=True)

        profile_path = cfg_dir / f"config_{slug}.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

        active_path = cfg_dir / "config.json"
        shutil.copyfile(profile_path, active_path)

        print("\n✔ Nova unidade criada e ativada!")
        print(f"   Perfil salvo   : {profile_path}")
        print(f"   Perfil ativo   : {active_path}")
        print("   Agora gere a Crossword (opção 1).")
