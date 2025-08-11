# src/engligen/app.py
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Mantém os imports exatamente no padrão atual do projeto
from engligen.core.crossword import Crossword
from engligen.core.wordsearch import WordSearch
from engligen.rendering.clue_generator import ClueGenerator
from engligen.rendering.crossword_renderer import CrosswordRenderer
from engligen.rendering.wordsearch_renderer import WordSearchRenderer


class EngligenApp:
    """
    Orquestrador da aplicação:
      - Lê/salva config (data/config.json)
      - Resolve caminhos (data/, output/)
      - Carrega bancos de palavras
      - Dispara geração (Crossword / WordSearch)
      - Renderiza imagens e gera .txt de dicas
    """

    # -------------------- Infra --------------------
    def __init__(self) -> None:
        self.project_root = self._detect_project_root()
        self.data_dir = self.project_root / "data"
        self.wordlists_dir = self.data_dir / "wordlists"
        self.output_dir = self.project_root / "output"
        self.config_path = self.data_dir / "config.json"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wordlists_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.config: Dict = self._load_config() or {}

        # caminhos de histórico (permitir override via config)
        used_cfg = (self.config.get("used_words") or {})
        self.used_common_path = self.wordlists_dir / (used_cfg.get("common_file") or "used_common.json")
        self.used_thematic_path = self.wordlists_dir / (used_cfg.get("themed_file") or "used_thematic.json")

    def _detect_project_root(self) -> Path:
        here = Path(__file__).resolve()
        for p in [here, *here.parents]:
            if (p / "data").exists():
                return p
        return Path.cwd()

    def _as_path(self, rel: str | Path) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else (self.project_root / p)

    # -------------------- Config --------------------
    def _load_config(self) -> Optional[Dict]:
        if not self.config_path.exists():
            return None
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_config(self, cfg: Dict) -> None:
        self.config = cfg or {}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    # -------------------- IO util --------------------
    def _resolve_file(self, rel: str | Path | None) -> Optional[Path]:
        if not rel:
            return None
        p = self._as_path(rel)
        return p if p.exists() else None

    def _read_json_list(self, path: Path) -> Optional[List[Dict]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except Exception:
            print(f"❌ ERRO ao ler JSON: {path}")
            return None

    def _load_words_file(self, path: Path) -> Optional[List[Dict]]:
        arr = self._read_json_list(path)
        if arr is None:
            return None
        # saneamento mínimo
        out: List[Dict] = []
        for it in arr:
            if not isinstance(it, dict):
                continue
            w = (it.get("word") or "").strip().upper()
            if w:
                out.append({"word": w, "clue": it.get("clue") or ""})
        return out

    # -------------------- Histórico --------------------
    def _load_used(self, path: Path) -> Set[str]:
        if not path.exists():
            return set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if isinstance(arr, list):
                return set((w or "").upper() for w in arr if isinstance(w, str))
        except Exception:
            pass
        return set()

    def _save_used(self, path: Path, used: Set[str]) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sorted(list(used)), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Não foi possível salvar histórico '{path.name}': {e}")

    # -------------------- Wordlists via config --------------------
    def resolve_wordlists_from_config(
        self,
        *,
        common_override: Optional[str] = None,
        themed_overrides: Optional[List[str]] = None,
    ) -> Tuple[Optional[Path], List[Path]]:
        """
        Resolve caminhos considerando overrides do menu e (na ausência) o data/config.json.
        Suporta 'course.active_unit' e 'include_previous_units'.
        """
        # Overrides do menu (preferência total)
        common_file: Optional[Path] = self._resolve_file(common_override) if common_override else None
        themed_files: List[Path] = []
        if themed_overrides:
            for t in themed_overrides:
                p = self._resolve_file(t)
                if p is not None:
                    themed_files.append(p)

        if themed_files:
            return (common_file, themed_files)

        # Fallback: usar config.json
        cfg = self.config or {}
        if not common_file and cfg.get("common_words_file"):
            common_file = self._resolve_file(cfg.get("common_words_file"))

        course = cfg.get("course") or {}
        include_prev = bool(course.get("include_previous_units"))
        active_slug = (course.get("active_unit") or "")
        units = course.get("units") or []

        themed_map = {u.get("slug"): u.get("themed_words_file") for u in units if isinstance(u, dict)}
        order = [u.get("slug") for u in units if isinstance(u, dict)]
        if active_slug and active_slug in themed_map:
            if include_prev and order:
                upto = order.index(active_slug) + 1 if active_slug in order else len(order)
                slugs = order[:upto]
            else:
                slugs = [active_slug]
            for slug in slugs:
                fp = themed_map.get(slug)
                p = self._resolve_file(fp) if fp else None
                if p is not None:
                    themed_files.append(p)

        return (common_file, themed_files)

    # ======================================================================
    #                            CROSSWORD
    # ======================================================================
    def executar_gerador_crossword(
        self,
        *,
        output_basename: str,
        altura: int,
        largura: int,
        seed: Optional[int] = None,
        reset: bool = False,
        ink_saver: bool = True,
        header_text: Optional[str] = None,
        common_file_override: Optional[str] = None,
        themed_files_override: Optional[List[str]] = None,
        prefill_words_count: int = 0,
        prefill_prefer_thematic: bool = True,
    ) -> bool:
        # Resolve arquivos (overrides > config.json)
        common_file, themed_files = self.resolve_wordlists_from_config(
            common_override=common_file_override,
            themed_overrides=themed_files_override,
        )
        if not themed_files:
            print("❌ ERRO: Nenhum arquivo temático definido.")
            return False

        # Carrega bancos
        themed_data: List[Dict] = []
        for p in themed_files:
            data = self._load_words_file(p)
            if data is None:
                return False
            themed_data.extend(data)

        common_data: List[Dict] = []
        if common_file and common_file.exists():
            tmp = self._load_words_file(common_file)
            if tmp is None:
                return False
            common_data = tmp

        themed_set_all = set(it["word"] for it in themed_data)
        # Histórico (considera reset)
        used_them = set() if reset else self._load_used(self.used_thematic_path)
        used_com = set() if reset else self._load_used(self.used_common_path)

        # Filtra já usados
        themed_words = [it["word"] for it in themed_data if it["word"] not in used_them]
        common_words = [it["word"] for it in common_data if it["word"] not in used_com]

        if not themed_words and not common_words:
            print("❌ ERRO: Sem palavras disponíveis (todas já usadas?).")
            return False

        # Seed global (o core usa random do módulo)
        if seed is not None:
            try:
                random.seed(int(seed))
            except Exception:
                pass

        # Instancia o gerador de cruzadas conforme a API do core
        cw = Crossword(
            themed_words=themed_words,
            common_words=common_words,
            num_attempts=50,
            max_size=(int(altura), int(largura)),
            target_density=0.70,
        )
        ok = cw.generate()
        if not ok or not cw.placed_words:
            print("❌ Não foi possível montar uma grade válida. Tente reduzir a lista.")
            return False

        # Mapa de dicas (palavras efetivamente colocadas)
        clue_by_word: Dict[str, str] = {}
        placed_words_set = set(cw.placed_words.keys())
        for it in themed_data + common_data:
            w = it.get("word", "")
            if w and w in placed_words_set:
                clue_by_word[w] = it.get("clue", "") or ""

        # Atualiza históricos apenas com as colocadas
        for w in placed_words_set:
            if w in set(it["word"] for it in themed_data):
                used_them.add(w)
            elif w in set(it["word"] for it in common_data):
                used_com.add(w)
        self._save_used(self.used_thematic_path, used_them)
        self._save_used(self.used_common_path, used_com)
        print(f"✔️  used_thematic.json: {len(used_them)} itens.")
        print(f"✔️  used_common.json: {len(used_com)} itens.")

        # Gera arquivo de dicas
        cg = ClueGenerator(cw, clue_by_word)
        clues_path = self.output_dir / f"{output_basename}_clues.txt"
        cg.generate_text_file(str(clues_path))

        # Prefill por PALAVRAS inteiras (opcional)
        prefilled_cells: Set[Tuple[int, int]] = set()
        if prefill_words_count and prefill_words_count > 0:
            ordered = list(placed_words_set)
            if prefill_prefer_thematic:
                ordered.sort(key=lambda w: (0 if w in themed_set_all else 1, -len(w)))
            else:
                ordered.sort(key=lambda w: -len(w))
            pick = ordered[: int(prefill_words_count)]

            # converte cada palavra em coordenadas a partir de placed_words
            for w in pick:
                info = cw.placed_words[w]  # {'row','col','direction'}
                r0, c0 = int(info["row"]), int(info["col"])
                dname = info["direction"]
                dr, dc = cw.directions[dname]
                for i in range(len(w)):
                    prefilled_cells.add((r0 + i * dr, c0 + i * dc))

        # Renderização
        renderer = CrosswordRenderer(
            cw,
            cg,
            cell_size=40,
            padding=25,
            ink_saver=bool(ink_saver),
            header_text=header_text,
        )
        if hasattr(renderer, "prefilled_positions"):
            renderer.prefilled_positions = prefilled_cells

        ex_path = self.output_dir / f"{output_basename}_exercicio.png"
        an_path = self.output_dir / f"{output_basename}_respostas.png"
        renderer.generate_image(str(ex_path), answers=False)
        renderer.generate_image(str(an_path), answers=True)

        print(f"📦 Saída: {self.output_dir}")
        print(f"   - {ex_path.name}")
        print(f"   - {an_path.name}")
        print(f"   - {clues_path.name}")
        print("🎉 Tudo pronto!")
        return True

    # ======================================================================
    #                            WORDSEARCH
    # ======================================================================
    def executar_gerador_wordsearch(
        self,
        *,
        output_basename: str,
        size: int,
        allow_fallback_common: bool = True,
        common_file_override: Optional[str] = None,
        themed_files_override: Optional[List[str]] = None,
        highlight_style: str = "fill",   # "fill" | "stroke"
        stroke_width: int = 5,
        # knobs adicionais (cap/ocupação alvo) – opcionais, lidos de config se não vierem:
        max_words: Optional[int] = None,
        min_words: int = 12,
        target_occupancy: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> bool:
        # Carrega preferências do WS da config (se não vierem por parâmetro)
        ws_cfg = (self.config.get("wordsearch") or {})
        if target_occupancy is None:
            target_occupancy = ws_cfg.get("target_occupancy")
        if max_words is None:
            cfg_max = ws_cfg.get("max_words")
            max_words = int(cfg_max) if isinstance(cfg_max, int) else None
        if not isinstance(min_words, int) or min_words < 1:
            min_words = int(ws_cfg.get("min_words", 12) or 12)

        # Resolve arquivos
        common_file, themed_files = self.resolve_wordlists_from_config(
            common_override=common_file_override,
            themed_overrides=themed_files_override,
        )
        if not themed_files:
            print("❌ ERRO: Nenhum arquivo temático definido para o WordSearch.")
            return False

        # Carrega bancos
        themed_data: List[Dict] = []
        for p in themed_files:
            data = self._load_words_file(p)
            if data is None:
                return False
            themed_data.extend(data)
        themed_words_all = [it["word"] for it in themed_data]
        themed_set = set(themed_words_all)

        common_words_all: List[str] = []
        if allow_fallback_common and common_file and common_file.exists():
            tmp = self._load_words_file(common_file)
            if tmp:
                common_words_all = [it["word"] for it in tmp]
        common_set = set(common_words_all)

        # Históricos
        used_them = self._load_used(self.used_thematic_path)
        used_com = self._load_used(self.used_common_path)

        # Filtra já usados
        themed_words = [w for w in themed_words_all if w not in used_them]
        common_words = [w for w in common_words_all if w not in used_com]

        # Candidatos (temático primeiro)
        words = list(dict.fromkeys(themed_words))

        # Completa mínimo com coringa se habilitado
        if allow_fallback_common and common_words and len(words) < min_words:
            for w in common_words:
                if w not in words:
                    words.append(w)
                if len(words) >= min_words:
                    break

        if not words:
            print("❌ ERRO: Nenhuma palavra disponível para o WordSearch.")
            return False

        # Cálculo de CAP da lista
        cap: int
        if isinstance(max_words, int) and max_words > 0:
            cap = max(1, int(max_words))
        elif isinstance(target_occupancy, (float, int)) and 0 < float(target_occupancy) <= 1.0:
            occ = float(target_occupancy)
            avg_len = sum(len(w) for w in words[:50]) / max(1, min(50, len(words)))
            overlap_factor = 0.85
            est = int(round((occ * (size * size)) / max(2.0, avg_len) / overlap_factor))
            cap = max(min_words, min(len(words), est))
        else:
            base = 24 if int(size) == 15 else int(round(24 * (int(size) * int(size)) / (15 * 15)))
            cap = max(min_words, min(len(words), base))

        # Amostra com leve aleatoriedade preservando prioridade por tamanho
        words_sorted = sorted(words, key=len, reverse=True)
        try:
            rng = random.Random(int(seed)) if seed is not None else random.Random()
        except Exception:
            rng = random.Random()
        pool = words_sorted[:min(len(words_sorted), cap * 2)]
        rng.shuffle(pool)
        selected = pool[:cap]

        # Gerar
        ws = WordSearch(words=selected, size=int(size))
        ws.generate()

        # Palavras efetivamente posicionadas
        placed = list(ws.placed_words.keys())

        # Clues (somente as colocadas, ordem alfabética p/ correção fácil)
        clues_path = self.output_dir / f"{output_basename}_clues.txt"
        with open(clues_path, "w", encoding="utf-8") as f:
            for i, w in enumerate(sorted(placed), 1):
                f.write(f"{i}. {w}\n")
        print(f"📄 Arquivo de dicas '{clues_path.name}' gerado.")

        # Atualiza históricos com APENAS as colocadas
        for w in placed:
            if w in themed_set:
                used_them.add(w)
            elif w in common_set:
                used_com.add(w)
        self._save_used(self.used_thematic_path, used_them)
        self._save_used(self.used_common_path, used_com)

        # Render
        renderer = WordSearchRenderer(
            ws,
            cell_size=40,
            padding=25,
            highlight_style=(highlight_style or "fill"),
            stroke_width=int(stroke_width or 5),
        )
        ex = self.output_dir / f"{output_basename}_exercicio.png"
        an = self.output_dir / f"{output_basename}_respostas.png"
        renderer.generate_image(filename=str(ex), answers=False)
        renderer.generate_image(filename=str(an), answers=True)
        print(f"📦 Saída: {self.output_dir}")
        print(f"   - {ex.name}")
        print(f"   - {an.name}")
        print(f"   - {clues_path.name}")
        print("🎉 Tudo pronto!")
        return True
