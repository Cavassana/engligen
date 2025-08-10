
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from engligen.core.crossword import Crossword
from engligen.core.word_search import WordSearch
from engligen.rendering.clue_generator import ClueGenerator
from engligen.rendering.crossword_renderer import CrosswordRenderer
from engligen.rendering.wordsearch_renderer import WordSearchRenderer


class EngligenApp:
    def __init__(self) -> None:
        self.project_root: Path = Path(__file__).resolve().parents[2]
        self.config: Dict[str, Any] = self._load_config()

        used_cfg = self.config.get("used_words", {}) or {}
        self.path_used_common: Path = self._as_path(used_cfg.get("common_file", "data/wordlists/used_common.json"))
        self.path_used_thematic: Path = self._as_path(used_cfg.get("themed_file", "data/wordlists/used_thematic.json"))
        self.path_used_legacy: Path = self._as_path("data/wordlists/used_words.json")

        # Migração do legado
        if self.path_used_legacy.exists() and (not self.path_used_common.exists() and not self.path_used_thematic.exists()):
            try:
                with open(self.path_used_legacy, "r", encoding="utf-8") as f:
                    legacy = set(json.load(f))
            except Exception:
                legacy = set()
            self._persist_set(self.path_used_common, legacy, label="(migração) used_common.json")
            self._persist_set(self.path_used_thematic, legacy, label="(migração) used_thematic.json")
            print("ℹ️  Migração: histórico antigo replicado para common e thematic.")

    # ---------------- Utils ----------------

    def _resolve_file(self, maybe_rel: str) -> Path:
        """Resolve path relative to project_root when not absolute."""
        p = Path(maybe_rel)
        return p if p.is_absolute() else (self.project_root / p).resolve()


    def _as_path(self, rel: str) -> Path:
        return (self.project_root / rel).resolve()

    def _load_config(self) -> Dict[str, Any]:
        cfg = self.project_root / "data" / "config.json"
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            print(f"⚠️  AVISO: Config inválida em '{cfg}': {e}")
            return {}

    def _persist_set(self, path: Path, items: Set[str], label: Optional[str] = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(items)), f, indent=2, ensure_ascii=False)
        if label:
            print(f"✔️  {label}: {len(items)} itens.")

    def _load_set(self, path: Path) -> Set[str]:
        if not path.exists():
            return set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()

    def _carregar_dados_palavras(self, relpath: str) -> Optional[List[Dict[str, str]]]:
        try:
            with open(self._as_path(relpath), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ ERRO ao ler '{relpath}': {e}")
            return None

    # ---------- Helper: reconstruir palavra na grade ----------

    def _trace_word_positions(self, start_rc: Tuple[int, int], direction: str, grid: List[List[Optional[str]]]) -> Tuple[str, List[Tuple[int, int]]]:
        r, c = start_rc
        dr, dc = (0, 1) if direction == "horizontal" else (1, 0)
        letters: List[str] = []
        pos: List[Tuple[int, int]] = []
        R, C = len(grid), len(grid[0])
        while 0 <= r < R and 0 <= c < C:
            ch = grid[r][c]
            if not ch:
                break
            letters.append(ch)
            pos.append((r, c))
            r += dr
            c += dc
        return ("".join(letters).upper(), pos)

    # ---------------------- Crossword ----------------------

    def executar_gerador_crossword(
        self,
        output_basename: str,
        *,
        common_file_override: Optional[str] = None,
        themed_files_override: Optional[list[str]] = None,
        altura: int,
        largura: int,
        seed: Optional[int],
        reset: bool,  # ignorado (sem reset global)
        ink_saver: Optional[bool] = None,
        header_text: Optional[str] = None,
        watermark_text: Optional[str] = None,
        arrow_gap_px: Optional[int] = None,
        corner_pad: Optional[int] = None,
        # Prefill de letras
        prefill_mode: Optional[str] = None,   # "first" | "percent" | None
        prefill_percent: Optional[float] = None,
        prefill_include_across: Optional[bool] = None,
        prefill_include_down: Optional[bool] = None,
        # Prefill de PALAVRAS
        prefill_words_count: Optional[int] = None,
        prefill_prefer_thematic: Optional[bool] = True,
        active_unit_slug: Optional[str] = None,
    ) -> bool:

        # Curso / units
        # Overrides de arquivos para esta geração
        course = self.config.get("course") or {}
        units: List[Dict[str, Any]] = course.get("units") or []
        include_prev = bool(course.get("include_previous_units", True))
        unit_slug_cfg = course.get("active_unit")
        unit_idx_cfg = course.get("active_unit_index")
        unit_slug = active_unit_slug or unit_slug_cfg

        themed_files: List[str] = []
        if units:
            idx_active = 0
            if unit_slug is not None:
                for i, u in enumerate(units):
                    if str(u.get("slug")) == str(unit_slug):
                        idx_active = i
                        break
            elif isinstance(unit_idx_cfg, int) and 0 <= unit_idx_cfg < len(units):
                idx_active = unit_idx_cfg
            themed_files = [u.get("themed_words_file") for u in (units[: idx_active + 1] if include_prev else [units[idx_active]]) if u.get("themed_words_file")]
        else:
            if self.config.get("themed_words_file"):
                themed_files = [self.config.get("themed_words_file")]

        common_file = str(self._resolve_file(common_file_override)) if common_file_override else self.config.get("common_words_file")
        if not themed_files or not common_file:
            print("❌ ERRO: Configure 'common_words_file' e pelo menos um 'themed_words_file'.")
            return False

        # Seed global
        if seed is not None:
            random.seed(seed)
            print(f"🎯 Seed configurada: {seed}")

        print("⚙️  Iniciando geração da Crossword...")

        themed_data_all: List[Dict[str, str]] = []
        for p in themed_files:
            data = self._carregar_dados_palavras(p)
            if not data: return False
            themed_data_all.extend(data)

        common_data = self._carregar_dados_palavras(common_file)
        if not common_data: return False

        used_common = self._load_set(self.path_used_common)
        used_thematic = self._load_set(self.path_used_thematic)

        clues_map: Dict[str, str] = {}
        for item in themed_data_all + common_data:
            w = (item.get("word") or "").upper()
            if w:
                clues_map[w] = item.get("clue", f'Dica para "{w}" não encontrada.')

        themed_pool_set: Set[str] = { (item.get("word") or "").upper() for item in themed_data_all if item.get("word") }
        common_pool_set: Set[str] = { (item.get("word") or "").upper() for item in common_data if item.get("word") }

        themed_disponivel = list(themed_pool_set - used_thematic)
        common_disponivel = list(common_pool_set - used_common)

        if not themed_disponivel:
            print("❌ ERRO: Banco temático esgotado; adicione mais itens.")
            return False

        crossword = Crossword(
            themed_words=themed_disponivel,
            common_words=common_disponivel,
            max_size=(altura, largura)
        )
        if not crossword.generate():
            print("❌ FALHA: algoritmo não encontrou solução válida.")
            return False
        print(f"✅ SUCESSO! Grade com {len(crossword.placed_words)} palavras.")

        # Atualiza histórico
        placed = set(crossword.placed_words.keys())
        self._persist_set(self.path_used_thematic, used_thematic.union(placed & themed_pool_set), label="used_thematic.json")
        self._persist_set(self.path_used_common, used_common.union(placed & common_pool_set), label="used_common.json")

        # Saída de dicas
        out_dir = self._as_path("output"); out_dir.mkdir(parents=True, exist_ok=True)
        clue_gen = ClueGenerator(crossword, clues_map)
        clue_gen.generate_text_file(filename=str(out_dir / f"{output_basename}_clues.txt"))

        # Renderer (overrides + defaults)
        renderer_cfg = (self.config.get("renderer") or {}).copy()

        def coalesce(cfg_key: str, override: Optional[Any], default: Any) -> Any:
            return default if override is None and renderer_cfg.get(cfg_key) is None else (override if override is not None else renderer_cfg.get(cfg_key, default))

        ink_saver_val: bool = bool(coalesce("ink_saver", ink_saver, True))
        header_text_val: Optional[str] = coalesce("header_text", header_text, None)
        watermark_text_val: Optional[str] = coalesce("watermark_text", watermark_text, None)
        if isinstance(watermark_text_val, str) and watermark_text_val.strip() == "":
            watermark_text_val = None
        arrow_gap_px_val: Optional[int] = coalesce("arrow_gap_px", arrow_gap_px, None)
        corner_pad_val: int = int(coalesce("corner_pad", corner_pad, 2))

        renderer = CrosswordRenderer(
            crossword, clue_gen,
            cell_size=40, padding=25,
            ink_saver=ink_saver_val,
            header_text=header_text_val,
            watermark_text=watermark_text_val,
            corner_pad=corner_pad_val,
            arrow_gap_px=arrow_gap_px_val,
        )

        # ----- Prefill -----
        if prefill_words_count and prefill_words_count > 0:
            # catálogo
            starts: List[Tuple[Tuple[int, int], str]] = []
            for (rc, infos) in clue_gen.clue_positions.items():
                for info in infos:
                    starts.append((rc, info["dir"]))
            catalog: List[Tuple[str, List[Tuple[int, int]]]] = []
            for (rc, direction) in starts:
                w, pos = self._trace_word_positions(rc, direction, crossword.grid)
                if w: catalog.append((w, pos))

            thematic_items = [(w, p) for (w, p) in catalog if w in themed_pool_set]
            other_items = [(w, p) for (w, p) in catalog if w not in themed_pool_set]

            rng = random.Random(seed)
            selection: List[Tuple[str, List[Tuple[int, int]]]] = []
            pool = thematic_items[:] if prefill_prefer_thematic else (thematic_items + other_items)
            rng.shuffle(pool)
            for item in pool:
                if len(selection) >= prefill_words_count: break
                selection.append(item)
            if prefill_prefer_thematic and len(selection) < prefill_words_count:
                extra = other_items[:]; rng.shuffle(extra)
                for item in extra:
                    if len(selection) >= prefill_words_count: break
                    if item not in selection: selection.append(item)

            prefilled: Set[Tuple[int, int]] = set()
            for _, positions in selection: prefilled.update(positions)
            renderer.prefilled_positions = prefilled
            print(f"✍️  Prefill: {len(selection)} palavra(s) completa(s).")

        else:
            prefill_cfg = (renderer_cfg.get("prefill") or {}).copy()
            mode: Optional[str] = (prefill_mode if prefill_mode is not None else prefill_cfg.get("mode"))
            mode = mode.lower() if isinstance(mode, str) else None

            if mode == "first":
                inc_a = bool(prefill_include_across if prefill_include_across is not None else prefill_cfg.get("include_across", True))
                inc_d = bool(prefill_include_down   if prefill_include_down   is not None else prefill_cfg.get("include_down", False))
                renderer.prefilled_positions = renderer.compute_prefill_first_letters(inc_a, inc_d)
                print(f"✍️  Prefill: primeiras letras — Across={inc_a}, Down={inc_d}")
            elif mode == "percent":
                pct = float(prefill_percent if prefill_percent is not None else prefill_cfg.get("percent", 10.0))
                seed_pf = prefill_cfg.get("seed", seed)
                renderer.prefilled_positions = renderer.compute_prefill_percent(percent=pct, seed=seed_pf)
                print(f"✍️  Prefill: {pct:.1f}% das letras (seed={seed_pf})")

        # Imagens
        ex_path = out_dir / f"{output_basename}_exercicio.png"
        ans_path = out_dir / f"{output_basename}_respostas.png"
        renderer.generate_image(str(ex_path), answers=False)
        renderer.generate_image(str(ans_path), answers=True)

        print(f"\n📦 Saída: {out_dir.resolve()}")
        print(f"   - {ex_path.name}")
        print(f"   - {ans_path.name}")
        print(f"   - {out_dir.name}/{output_basename}_clues.txt")
        print("🎉 Tudo pronto!")
        return True

    # ---------------------- WordSearch ----------------------

    def executar_gerador_wordsearch(self, output_basename: str, size: int, allow_fallback_common: bool = True,
                                  common_file_override: Optional[str] = None,
                                  themed_files_override: Optional[list[str]] = None) -> bool:
        # Overrides de arquivos para esta geração
        course = self.config.get("course") or {}
        units: List[Dict[str, Any]] = course.get("units") or []
        include_prev = bool(course.get("include_previous_units", True))

        if units:
            unit_slug = course.get("active_unit")
            unit_idx_cfg = course.get("active_unit_index")
            themed_files: List[str] = []
            idx_active = 0
            if unit_slug is not None:
                for i, u in enumerate(units):
                    if str(u.get("slug")) == str(unit_slug):
                        idx_active = i; break
            elif isinstance(unit_idx_cfg, int) and 0 <= unit_idx_cfg < len(units):
                idx_active = unit_idx_cfg
            themed_files = [u.get("themed_words_file") for u in (units[: idx_active + 1] if include_prev else [units[idx_active]]) if u.get("themed_words_file")]
        else:
            themed_files = [self.config.get("themed_words_file")] if self.config.get("themed_words_file") else []

        if not themed_files:
            print("❌ ERRO: Nenhum arquivo temático definido para o WordSearch.")
            return False

        themed_data_all: List[Dict[str, str]] = []
        for p in themed_files:
            data = self._carregar_dados_palavras(p)
            if not data: return False
            themed_data_all.extend(data)

        common_file = str(self._resolve_file(common_file_override)) if common_file_override else self.config.get("common_words_file")
        if not common_file:
            print("❌ ERRO: 'common_words_file' ausente no config.")
            return False
        common_data = self._carregar_dados_palavras(common_file) or []

        used_thematic = self._load_set(self.path_used_thematic)
        used_common = self._load_set(self.path_used_common)

        themed_pool: Set[str] = { (it.get("word") or "").upper() for it in themed_data_all if it.get("word") }
        common_pool: Set[str] = { (it.get("word") or "").upper() for it in common_data if it.get("word") }

        remaining = sorted(list(themed_pool - used_thematic))
        words_for_ws: List[str] = remaining

        if not words_for_ws:
            print("ℹ️  Sem palavras temáticas restantes para o caça-palavras.")
            if not allow_fallback_common:
                return False
            common_remaining = sorted(list(common_pool - used_common))
            if not common_remaining:
                print("ℹ️  Banco coringa também esgotado.")
                return False
            # Seleciona um conjunto razoável baseado no tamanho
            target = max(12, min(40, size + 5))
            rng = random.Random()
            rng.shuffle(common_remaining)
            words_for_ws = common_remaining[:target]
            print(f"↳ Usando {len(words_for_ws)} palavras do banco coringa.")

        # Map de dicas (usa só o que foi realmente selecionado)
        lookup: Dict[str, str] = {}
        for item in themed_data_all + common_data:
            w = (item.get("word") or "").upper()
            if w:
                lookup[w] = item.get("clue", f'Dica para "{w}" não encontrada.')

        ws = WordSearch(words=words_for_ws, size=size)
        if not ws.generate():
            print("❌ FALHA: não foi possível gerar o caça-palavras.")
            return False
        print(f"✅ SUCESSO! Caça-palavras com {len(ws.placed_words)} palavras.")

        out = self._as_path("output"); out.mkdir(exist_ok=True)

        clues_path = out / f"{output_basename}_clues.txt"
        with open(clues_path, "w", encoding="utf-8") as f:
            header = "DICAS"; f.write(f"{header}\n"); f.write(f"{'-'*len(header)}\n")
            for i, w in enumerate(sorted(ws.placed_words.keys()), 1):
                default_clue = f'Dica para "{w}" não encontrada.'
                clue = lookup.get(w, default_clue)
                f.write(f"{i}. {clue}\n")
        print(f"📄 Arquivo de dicas '{clues_path.name}' gerado.")

        renderer = WordSearchRenderer(ws)
        renderer.generate_image(filename=str(out / f"{output_basename}_exercicio.png"), answers=False)
        renderer.generate_image(filename=str(out / f"{output_basename}_respostas.png"), answers=True)

        print(f"\n📦 Saída: {out.resolve()}")
        print("🎉 Tudo pronto!")
        return True
