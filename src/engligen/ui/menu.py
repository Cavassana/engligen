from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Set

from engligen.app import EngligenApp


# ----------------- helpers -----------------
def _ask(prompt: str, default: Optional[str] = None) -> str:
    if default is None:
        v = input(f"{prompt}: ").strip()
    else:
        v = input(f"{prompt} [{default}]: ").strip()
        if v == "":
            return default
    return v

def _ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    hint = "Enter=Sim | s/n" if default_yes else "Enter=Não | s/n"
    while True:
        v = input(f"{prompt} [{hint}]: ").strip().lower()
        if v == "" and default_yes: return True
        if v == "" and not default_yes: return False
        if v in ("s","sim","y","yes"): return True
        if v in ("n","nao","não","no"): return False
        print("Resposta inválida. Digite s/n ou Enter para padrão.")

def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if raw == "":
            return int(default)
        try:
            return int(raw)
        except ValueError:
            print("Valor inválido (inteiro).")

def _ask_float(prompt: str, default: float) -> float:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if raw == "":
            return float(default)
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            print("Valor inválido (número). Use ponto ou vírgula, ex.: 0.4")

def _confirm_value(label: str, val: str) -> bool:
    return _ask_yes_no(f"Confirma o valor: '{val}'?", True)


# ----------------- autodetecção -----------------
def _scan_wordlists(root: Path) -> List[Path]:
    root.mkdir(parents=True, exist_ok=True)
    out: List[Path] = []
    for p in sorted(root.glob("*.json")):
        if p.name.startswith("used_"): continue
        if p.name.startswith("config"): continue
        out.append(p)
    return out

def _suggest_role(name: str) -> str:
    n = name.lower()
    if "general" in n or "common" in n or "coringa" in n:
        return "common"
    if "thematic" in n or "unit" in n or "tema" in n or "u" in n:
        return "themed"
    return "?"

def _pick_files_interactive(base: Path) -> Tuple[Optional[str], List[str]]:
    files = _scan_wordlists(base)
    if not files:
        print("Nenhum .json encontrado em data/wordlists/.")
        return (None, [])

    print("\nArquivos encontrados em data/wordlists:")
    details: Dict[str, Tuple[int,int]] = {}
    for i, p in enumerate(files, 1):
        try:
            with open(p, "r", encoding="utf-8") as f:
                arr = json.load(f)
            valid = sum(1 for it in arr if isinstance(it, dict) and (it.get('word') or ""))
            total = len(arr) if isinstance(arr, list) else 0
        except Exception:
            valid, total = 0, 0
        details[p.name] = (valid, total)
        print(f"   {i}) {p.name:<28}  — itens: {valid}/{total}  — sugestão: {_suggest_role(p.name)}")

    common = None
    themed = None
    for p in files:
        role = _suggest_role(p.name)
        if role == "common" and common is None:
            common = p
        if role == "themed" and themed is None:
            themed = p
    if common and themed:
        print(f"Proposta: CORINGA = {common.name} ; TEMÁTICO = {themed.name}")
        if _ask_yes_no("Usar essa combinação?", True):
            return (str(common), [str(themed)])

    # escolha manual
    raw_c = input("Informe o NÚMERO do CORINGA (ou Enter para pular): ").strip()
    common_sel = None
    if raw_c:
        try:
            idx = int(raw_c) - 1
            if 0 <= idx < len(files):
                common_sel = files[idx]
        except ValueError:
            pass
    raw_t = input("Informe o(s) NÚMERO(s) do(s) TEMÁTICO(s), separados por ';': ").strip()
    themed_sel: List[Path] = []
    if raw_t:
        for token in raw_t.replace(",", ";").split(";"):
            token = token.strip()
            if not token: continue
            try:
                x = int(token) - 1
                if 0 <= x < len(files):
                    themed_sel.append(files[x])
            except ValueError:
                pass

    if common_sel or themed_sel:
        return (str(common_sel) if common_sel else None, [str(p) for p in themed_sel])

    print("Seleção inválida.")
    return (None, [])


# ----------------- util local para reexecução assistida -----------------
def _to_abs(base: Path, maybe: Optional[str]) -> Optional[Path]:
    if not maybe:
        return None
    p = Path(maybe)
    return p if p.is_absolute() else (base / p)

def _load_words_only(fp: Path) -> List[str]:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            arr = json.load(f)
        out = []
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict):
                    w = (it.get("word") or "").strip().upper()
                    if w:
                        out.append(w)
        return out
    except Exception:
        return []

def _read_used(path: Path) -> Set[str]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if isinstance(arr, list):
                return set((x or "").upper() for x in arr if isinstance(x, str))
    except Exception:
        pass
    return set()


# ----------------- Menu -----------------
class Menu:
    def __init__(self) -> None:
        self.app = EngligenApp()
        self.project_root = self.app.project_root

    def run(self) -> None:
        while True:
            print("\n╔═════════════════════════════════════╗")
            print("║   Engligen: Gerador de Exercícios   ║")
            print("╠═════════════════════════════════════╣")
            print("║ 1) Gerar Palavra-Cruzada (Crossword)║")
            print("║ 2) Gerar Caça-Palavras (WordSearch) ║")
            print("║ 3) Iniciar NOVA UNIDADE (assistente)║")
            print("║ 4) Sair                             ║")
            print("╚═════════════════════════════════════╝")
            op = input("Escolha uma opção: ").strip()
            if op == "1":
                self._get_input_crossword()
            elif op == "2":
                self._get_input_wordsearch()
            elif op == "3":
                self._wizard_unidade()
            elif op == "4":
                print("\nSaindo. Até mais!")
                return
            else:
                print("Opção inválida.")

    # ---------- Crossword ----------
    def _run_crossword_with_recovery(
        self,
        *,
        basename: str,
        altura: int,
        largura: int,
        header: Optional[str],
        common_file: Optional[str],
        themed_files: List[str],
        prefill_words: int,
        prefer_thematic: bool,
    ) -> bool:
        """
        Executa o gerador. Se falhar, verifica se o motivo provável é falta de âncora
        temática (lista temática esgotada/curta) e oferece usar o CORINGA como 'temático'
        apenas nesta execução. Em caso afirmativo, reexecuta automaticamente.
        """
        # 1) tentativa normal
        ok = self.app.executar_gerador_crossword(
            output_basename=basename,
            altura=int(altura),
            largura=int(largura),
            header_text=(header if header != "" else None),
            common_file_override=common_file,
            themed_files_override=themed_files,
            prefill_words_count=int(prefill_words),
            prefill_prefer_thematic=prefer_thematic,
            reset=False,
        )
        if ok:
            return True

        # 2) diagnóstico leve dos arquivos escolhidos
        base = self.project_root
        themed_abs: List[Path] = []
        for t in themed_files or []:
            p = _to_abs(base, t)
            if p and p.exists():
                themed_abs.append(p)

        common_abs = _to_abs(base, common_file) if common_file else None

        # carrega palavras e aplica filtro de usadas
        used_them = _read_used(self.app.used_thematic_path)
        used_com = _read_used(self.app.used_common_path)

        themed_avail: List[str] = []
        for fp in themed_abs:
            themed_avail.extend([w for w in _load_words_only(fp) if w not in used_them])

        common_avail: List[str] = []
        if common_abs and common_abs.exists():
            common_avail = [w for w in _load_words_only(common_abs) if w not in used_com]

        # sinal de problema típico: não há temáticas disponíveis (após histórico)
        if len(themed_avail) == 0:
            print("\n❌ Falha ao gerar a cruzadinha com as palavras TEMÁTICAS disponíveis.")
            if not common_avail:
                print("   ➤ Não há palavras no CORINGA para ajudar na inicialização.")
                print("   ✖ Operação não concluída. Ajuste os bancos/seleção e tente novamente.")
                return False

            print("   Causa provável: a lista temÁtica ativa está vazia (ou toda usada).")
            print("   Proposta de correção automática:")
            print("     • Usar o arquivo CORINGA como fonte de sementes 'temáticas' nesta execução;")
            print("       (os arquivos originais NÃO serão alterados).")
            if _ask_yes_no("Aplicar esta correção e tentar novamente agora?", True):
                # reexecuta adicionando o common como 'temático' (além dos temáticos originais)
                themed_over = list(themed_files or [])
                if common_file:
                    themed_over = themed_over + [common_file]
                ok2 = self.app.executar_gerador_crossword(
                    output_basename=basename,
                    altura=int(altura),
                    largura=int(largura),
                    header_text=(header if header != "" else None),
                    common_file_override=common_file,
                    themed_files_override=themed_over,
                    prefill_words_count=int(prefill_words),
                    prefill_prefer_thematic=prefer_thematic,
                    reset=False,
                )
                if ok2:
                    print("✔️ Correção aplicada com sucesso.")
                    return True
                print("✖ Mesmo com a correção, não foi possível gerar a grade.")
                return False
            else:
                print("✖ Operação cancelada pelo usuário.")
                return False

        # Se chegou aqui, a falha não é (apenas) falta de temáticas.
        print("✖ Operação não concluída. Veja mensagens acima.")
        print("   Dicas: reduza largura/altura, diminua prefill por palavras, ou troque os bancos.")
        return False

    def _get_input_crossword(self) -> None:
        print("\n▶ Gerar Palavra-Cruzada")
        basename = _ask("Insira o nome-base do arquivo (ex: cw_01_unit_01)", default="teste")
        if not _confirm_value("nome-base", basename):
            print("Operação cancelada."); return

        altura = _ask_int("Altura (linhas)", 20)
        if not _ask_yes_no(f"Confirma o valor: {float(altura)}?", True): return
        largura = _ask_int("Largura (colunas)", 15)
        if not _ask_yes_no(f"Confirma o valor: {float(largura)}?", True): return

        # Mantido por compatibilidade visual (não é usado pelo app)
        seed = _ask("Seed (vazio = aleatória)", default="").strip() or None
        if seed and not _ask_yes_no(f"Confirma o valor: '{seed}'?", True): return

        common_file = None
        themed_files: List[str] = []
        if _ask_yes_no("Tentar DETECTAR automaticamente os arquivos em data/wordlists?", True):
            common_file, themed_files = _pick_files_interactive(self.project_root / "data" / "wordlists")

        # Mantido por compatibilidade visual (o renderer usa ink-saver por padrão no app)
        _ = _ask_yes_no("Usar modo ink-saver (fundo branco)?", True)

        header = _ask("Header (vazio = usar config)", default="")
        if not _ask_yes_no(f"Confirma o valor: '{header}'?", True): return

        # Prefill por PALAVRAS inteiras
        n_words = _ask_int("Quantas PALAVRAS completas deseja exibir? [0 = nenhuma]", 0)
        if not _ask_yes_no(f"Confirma o valor: {float(n_words)}?", True): return
        prefer_thematic = _ask_yes_no("Preferir palavras do banco TEMÁTICO ao escolher as exibidas?", True)

        ok = self._run_crossword_with_recovery(
            basename=basename,
            altura=int(altura),
            largura=int(largura),
            header=header,
            common_file=common_file,
            themed_files=themed_files,
            prefill_words=int(n_words),
            prefer_thematic=prefer_thematic,
        )
        if not ok:
            # _run_crossword_with_recovery já imprime mensagens detalhadas
            pass

    # ---------- WordSearch ----------
    def _get_input_wordsearch(self) -> None:
        print("\n▶ Gerar Caça-Palavras")
        basename = _ask("Insira o nome-base do arquivo (ex: ws_01_unit_01)", default="wordsearch")
        if not _confirm_value("nome-base", basename):
            print("Operação cancelada."); return

        size = _ask_int("Tamanho da grade (NxN)", 15)
        if not _ask_yes_no(f"Confirma o valor: {float(size)}?", True): return

        # seleção de arquivos
        common_file = None
        themed_files: List[str] = []
        if _ask_yes_no("Tentar DETECTAR automaticamente os arquivos em data/wordlists?", True):
            common_file, themed_files = _pick_files_interactive(self.project_root / "data" / "wordlists")

        fallback = _ask_yes_no("Se esgotar temáticas, completar com banco coringa?", True)

        # ---- NOVOS KNOBS: densidade e seed ----
        print("\nDensidade do caça-palavras:")
        print("  m) Limitar por quantidade (max_words)")
        print("  o) Alvo de ocupação (target_occupancy)")
        print("  p) Padrão")
        modo = input("Escolha [m/o/p] (Enter = m): ").strip().lower() or "m"

        max_words: Optional[int] = None
        target_occupancy: Optional[float] = None
        if modo == "m":
            max_words = _ask_int("max_words (quantas palavras no máximo)", 24)
        elif modo == "o":
            target_occupancy = _ask_float("target_occupancy (0.10–0.75 recomendado)", 0.40)

        seed_txt = _ask("Seed (vazio = aleatória)", default="42").strip()
        seed_val = int(seed_txt) if seed_txt != "" else None

        # estilo do gabarito
        def ask_style() -> str:
            while True:
                s = input("Estilo do destaque nas RESPOSTAS (fill=quadrinhos | stroke=linha) [fill]: ").strip().lower()
                if s == "": return "fill"
                if s in ("fill", "stroke"): return s
                print("Digite 'fill' ou 'stroke'.")
        style = ask_style()
        stroke = 5
        if style == "stroke":
            while True:
                raw = input("Espessura da LINHA (px) [5]: ").strip()
                if raw == "": break
                try:
                    v = int(raw)
                    if 1 <= v <= 20:
                        stroke = v; break
                except ValueError:
                    pass
                print("Informe um inteiro entre 1 e 20.")

        ok = self.app.executar_gerador_wordsearch(
            output_basename=basename,
            size=int(size),
            allow_fallback_common=fallback,
            common_file_override=common_file,
            themed_files_override=themed_files,
            highlight_style=style,
            stroke_width=stroke,
            # novos knobs:
            target_occupancy=target_occupancy,
            max_words=max_words,
            seed=seed_val,
        )
        if not ok:
            print("✖ Operação não concluída. Veja mensagens acima.")

    # ---------- Wizard de unidade ----------
    def _wizard_unidade(self) -> None:
        print("\n▶ Iniciar NOVA UNIDADE")
        slug = _ask("Slug da unidade (ex: u1)", default="u1")
        name = _ask("Nome da unidade (ex: Adam Smith)", default="Unit 1 — Adam Smith")
        themed = _ask("Arquivo TEMÁTICO (JSON)", default="data/wordlists/unit01_thematic_words.json")
        include_prev = _ask_yes_no("Incluir conteúdos de unidades anteriores?", True)

        cfg = self.app._load_config() or {}
        cfg.setdefault("course", {})
        cfg["course"]["active_unit"] = slug
        cfg["course"]["include_previous_units"] = include_prev
        units = cfg["course"].get("units") or []
        # substitui ou adiciona
        found = False
        for u in units:
            if u.get("slug") == slug:
                u["name"] = name
                u["themed_words_file"] = themed
                found = True
                break
        if not found:
            units.append({"slug": slug, "name": name, "themed_words_file": themed})
        cfg["course"]["units"] = units

        # salva como ativo
        self.app._save_config(cfg)
        print("✔️  Configuração salva em data/config.json e ativada.")


# compatível com o seu main atual: engligen.main importa este módulo e chama run()
def run() -> None:
    Menu().run()
