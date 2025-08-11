from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import random
import string
import unicodedata

class WordSearch:
    """
    Caça-palavras NxN com 8 direções (→ ← ↓ ↑ ↗ ↘ ↙ ↖),
    heurística orientada a interseções e controle de distribuição.

    Interface pública (compatível com seu renderer/app):
      - WordSearch(words: List[str], size: int = 15)
      - generate() -> None
      - .size : int
      - .grid : List[List[str]]   # N×N, letras A–Z
      - .placed_words : Dict[str, Dict[str,int]]  # {word:{r,c,dr,dc}}

    Observações:
      - Palavras são normalizadas (A–Z, sem acentos/traços/espaços).
      - O algoritmo tenta colocar TODAS as palavras fornecidas (na ordem por tamanho),
        priorizando candidatos com maior número de interseções.
    """

    # Direções (dr, dc): H/V + diagonais (ambas inclinações)
    _DIRS_ALL: List[Tuple[int, int]] = [
        (0, 1),  (0, -1),  (1, 0),  (-1, 0),   # → ← ↓ ↑
        (1, 1),  (-1, -1), (1, -1), (-1, 1)    # ↘ ↖ ↙ ↗
    ]
    # Direções "canônicas" (sem reverso explícito): direita, baixo, duas diagonais ascend/desc
    _DIRS_CANON: List[Tuple[int, int]] = [
        (0, 1), (1, 0), (1, 1), (-1, 1)        # → ↓ ↘ ↗
    ]

    # ---------- Parâmetros Heurísticos (ajuste fino sem mudar a API) ----------
    _MIN_INTERSEC_INIT: int = 1       # exigir ≥1 interseção desde o começo
    _ESCALATE_AFTER: int = 8          # após N palavras, tentar exigir ≥2
    _DIAGONAL_BONUS: float = 0.5      # bônus leve para diagonais (desagrupar linhas/colunas)
    _LINECOL_PENALTY: float = 0.05    # penalização de concentração por célula
    _TOPK_FRACTION: float = 0.25      # escolhe aleatoriamente dentro do top-k (diversidade)

    def __init__(
        self,
        words: List[str],
        size: int = 15,
        *,
        allow_reverse: bool = True,    # quando False, usa só direções canônicas
        seed: Optional[int] = None,
        alphabet: str = string.ascii_uppercase
    ) -> None:
        self.size = int(size)
        self._alphabet = alphabet
        self._allow_reverse = bool(allow_reverse)
        self._seed = seed

        # normaliza e ordena por tamanho (decrescente)
        base = [self._normalize(w) for w in (words or [])]
        base = [w for w in base if len(w) >= 2]
        # remove duplicadas preservando ordem
        seen = set()
        self.words: List[str] = []
        for w in base:
            if w not in seen:
                self.words.append(w)
                seen.add(w)
        self.words.sort(key=len, reverse=True)

        # inicializa grid e estruturas
        n = self.size
        self.grid: List[List[str]] = [["" for _ in range(n)] for _ in range(n)]
        # mapeia cada palavra colocada para {r,c,dr,dc}
        self.placed_words: Dict[str, Dict[str, int]] = {}

    # ------------------------- API principal -------------------------

    def generate(self) -> None:
        """Coloca as palavras no grid e preenche vazios com A–Z."""
        if self._seed is not None:
            random.seed(self._seed)

        n = self.size
        usos_linha = [0] * n
        usos_col = [0] * n

        dirs = self._DIRS_ALL if self._allow_reverse else self._DIRS_CANON

        placed_count = 0
        for w in self.words:
            # Escalonar exigência de interseções depois de algumas colocadas
            min_intersec = self._MIN_INTERSEC_INIT if placed_count < self._ESCALATE_AFTER else 2

            cand = self._best_candidate(w, dirs, min_intersec, usos_linha, usos_col)
            if cand is None:
                # relaxa para 1 interseção
                if min_intersec > 1:
                    cand = self._best_candidate(w, dirs, 1, usos_linha, usos_col)
            if cand is None:
                # se ainda assim não coube, tenta sem exigir interseção (último recurso)
                cand = self._best_candidate(w, dirs, 0, usos_linha, usos_col)
            if cand is None:
                # falhou: pula sem travar o processo
                continue

            score, r, c, dr, dc, k = cand
            self._place(r, c, dr, dc, w)

            # atualiza penalização de concentração para as células usadas
            rr, cc = r, c
            for _ in range(len(w)):
                usos_linha[rr] += 1
                usos_col[cc] += 1
                rr += dr
                cc += dc

            self.placed_words[w] = {"r": r, "c": c, "dr": dr, "dc": dc}
            placed_count += 1

        # completa com letras aleatórias
        for r in range(n):
            for c in range(n):
                if self.grid[r][c] == "":
                    self.grid[r][c] = random.choice(self._alphabet)

    # ------------------------- Heurística -------------------------

    def _best_candidate(
        self,
        w: str,
        dirs: List[Tuple[int, int]],
        min_intersec: int,
        usos_linha: List[int],
        usos_col: List[int],
    ) -> Optional[Tuple[float, int, int, int, int, int]]:
        """
        Retorna o melhor candidato (score, r, c, dr, dc, interseções) ou None.
        Estratégia: gerar inícios ancorados em letras já existentes e pontuar.
        """
        n = self.size
        L = len(w)
        candidates: List[Tuple[float, int, int, int, int, int]] = []

        # índice de posições por letra já no grid
        pos_by_char: Dict[str, List[Tuple[int, int]]] = {}
        for r in range(n):
            for c in range(n):
                ch = self.grid[r][c]
                if ch:
                    pos_by_char.setdefault(ch, []).append((r, c))

        # Se grid vazio: permitir qualquer início em qualquer direção
        if not pos_by_char:
            for (dr, dc) in dirs:
                for r in range(n):
                    for c in range(n):
                        if self._can_place(r, c, dr, dc, w):
                            k = 0
                            score = self._score_candidate(r, c, dr, dc, L, k, usos_linha, usos_col)
                            candidates.append((score, r, c, dr, dc, k))
        else:
            # Grid com letras: ancorar em coincidências w[i] sobre células já preenchidas
            for (dr, dc) in dirs:
                diag_bonus = self._DIAGONAL_BONUS if (dr != 0 and dc != 0) else 0.0
                for i, ch in enumerate(w):
                    for (rr, cc) in pos_by_char.get(ch, []):
                        r0 = rr - i * dr
                        c0 = cc - i * dc
                        if not self._can_place(r0, c0, dr, dc, w):
                            continue
                        k = self._count_intersections(r0, c0, dr, dc, w)
                        if k < min_intersec:
                            continue
                        score = self._score_candidate(r0, c0, dr, dc, L, k, usos_linha, usos_col, diag_bonus)
                        candidates.append((score, r0, c0, dr, dc, k))

        if not candidates:
            return None
        # ordena por score e escolhe aleatoriamente dentro do top-k (diversidade controlada)
        candidates.sort(key=lambda t: t[0], reverse=True)
        k_top = max(1, int(len(candidates) * max(0.05, min(0.9, self._TOPK_FRACTION))))
        return random.choice(candidates[:k_top])

    def _score_candidate(
        self,
        r: int, c: int, dr: int, dc: int,
        L: int, intersec: int,
        usos_linha: List[int], usos_col: List[int],
        diag_bonus: float = 0.0
    ) -> float:
        novas = L - intersec
        pen = self._linecol_penalty(usos_linha, usos_col, r, c, dr, dc, L, self._LINECOL_PENALTY)
        # 5*intersec premia cruzamentos, -1*novas limita enchimento, -pen evita “tubos”, +bônus quebra padrão
        return 5.0 * intersec - 1.0 * novas - pen + diag_bonus

    # ------------------------- Primitivas de grade -------------------------

    def _can_place(self, r: int, c: int, dr: int, dc: int, w: str) -> bool:
        n = self.size
        rr, cc = r, c
        for ch in w:
            if not (0 <= rr < n and 0 <= cc < n):
                return False
            cell = self.grid[rr][cc]
            if cell not in ("", ch):  # vazio ou igual
                return False
            rr += dr
            cc += dc
        return True

    def _place(self, r: int, c: int, dr: int, dc: int, w: str) -> None:
        rr, cc = r, c
        for ch in w:
            self.grid[rr][cc] = ch
            rr += dr
            cc += dc

    def _count_intersections(self, r: int, c: int, dr: int, dc: int, w: str) -> int:
        k = 0
        rr, cc = r, c
        for ch in w:
            if self.grid[rr][cc] == ch:
                k += 1
            rr += dr
            cc += dc
        return k

    def _linecol_penalty(
        self,
        usos_linha: List[int], usos_col: List[int],
        r: int, c: int, dr: int, dc: int, L: int,
        weight: float
    ) -> float:
        pen = 0.0
        rr, cc = r, c
        for _ in range(L):
            pen += weight * (usos_linha[rr] + usos_col[cc])
            rr += dr
            cc += dc
        return pen

    # ------------------------- Utilidades -------------------------

    @staticmethod
    def _normalize(w: str) -> str:
        # Remove acentos, espaços e caracteres não A–Z; mantém apenas A..Z
        if not isinstance(w, str):
            w = str(w or "")
        w = w.strip().upper()
        w = ''.join(
            ch for ch in unicodedata.normalize('NFD', w)
            if unicodedata.category(ch) != 'Mn'
        )
        # remove tudo que não for A..Z
        return ''.join(ch for ch in w if 'A' <= ch <= 'Z')

    @staticmethod
    def _arrow(dr: int, dc: int) -> str:
        # Mantido por compatibilidade (não é usado pelo renderer atual)
        if dr == 0 and dc == 1:  return "→"
        if dr == 0 and dc == -1: return "←"
        if dr == 1 and dc == 0:  return "↓"
        if dr == -1 and dc == 0: return "↑"
        if dr == 1 and dc == 1:  return "↘"
        if dr == -1 and dc == -1:return "↖"
        if dr == 1 and dc == -1: return "↙"
        if dr == -1 and dc == 1: return "↗"
        return "?"
