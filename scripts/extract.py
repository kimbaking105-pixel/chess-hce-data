#!/usr/bin/env python3
"""Извлечение тихих позиций из JSONL-партий (вывод selfplay.py).

Фильтр тишины (фиксирован заранее, одинаков для всех моделей):
  - сторона, которая ходит, не под шахом;
  - нет легального взятия (включая en passant) и нет превращения;
  - позиция не терминальная;
  - номер полухода от 10 до (len(moves) - 10), т.е. без дебютной и концовочной части.
Метка: результат партии с точки зрения стороны, которая ходит (1 / 0.5 / 0).

Отбор по фазе игры (ph: N,B=1, R=2, Q=4, max 24, обе стороны):
  - эндшпиль (ph <= 6): не больше --cap_end позиций на партию (случайный выбор);
  - остальное (ph >= 7, включая середину игры): берётся полностью
    (--cap_mid 0 = без ограничения, иначе ограничение на партию).
Повторы: позиции с одинаковой расстановкой (первые 4 поля FEN) пропускаются;
  повторы считаются в пределах одного запуска (--in ... за один вызов).

Выход: JSONL-строки {game_id, ply, fen, stm, label, ph, band} + фиксированный seed.
Оценки движков в метках не используются.
"""
import argparse
import collections
import json
import random

import chess

PHASE_W = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}


def label_for(result, stm):
    if result == "1-0":
        w = 1.0
    elif result == "0-1":
        w = 0.0
    elif result == "1/2-1/2":
        w = 0.5
    else:
        return None
    return w if stm == chess.WHITE else 1.0 - w


def quiet(board):
    if board.is_check() or board.is_game_over(claim_draw=True):
        return False
    for m in board.legal_moves:
        if board.is_capture(m) or m.promotion:
            return False
    return True


def phase(board):
    ph = 0
    for pt, w in PHASE_W.items():
        ph += w * (len(board.pieces(pt, chess.WHITE)) + len(board.pieces(pt, chess.BLACK)))
    return min(24, ph)


def band_of(ph):
    return "endgame" if ph <= 6 else "middle"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap_end", type=int, default=2,
                    help="макс. позиций эндшпиля (ph<=6) на партию")
    ap.add_argument("--cap_mid", type=int, default=0,
                    help="макс. позиций ph>=7 на партию (0 = без ограничения)")
    ap.add_argument("--min_ply", type=int, default=10)
    ap.add_argument("--tail", type=int, default=10)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    n_games = n_pos = n_dup = 0
    bands = collections.Counter()
    results = collections.Counter()
    seen = set()
    with open(args.out, "w") as out:
        for path in args.inp:
            for line in open(path):
                g = json.loads(line)
                n_games += 1
                start = g.get("start_fen", chess.STARTING_FEN)
                moves = g["moves"]
                board = chess.Board(start)
                cands = {"endgame": [], "middle": []}
                for i, uci in enumerate(moves):
                    if args.min_ply <= i < len(moves) - args.tail and quiet(board):
                        ph = phase(board)
                        cands[band_of(ph)].append((i, board.fen(), board.turn, ph))
                    board.push(chess.Move.from_uci(uci))
                if len(cands["endgame"]) > args.cap_end:
                    cands["endgame"] = rng.sample(cands["endgame"], args.cap_end)
                if args.cap_mid and len(cands["middle"]) > args.cap_mid:
                    cands["middle"] = rng.sample(cands["middle"], args.cap_mid)
                for b in ("middle", "endgame"):
                    for ply, fen, stm, ph in sorted(cands[b]):
                        key = " ".join(fen.split()[:4])
                        if key in seen:
                            n_dup += 1
                            continue
                        seen.add(key)
                        lab = label_for(g["result"], stm)
                        if lab is None:
                            continue
                        out.write(json.dumps({
                            "game_id": g["game_id"], "ply": ply, "fen": fen,
                            "stm": "w" if stm == chess.WHITE else "b", "label": lab,
                            "ph": ph, "band": b,
                        }) + "\n")
                        n_pos += 1
                        bands[b] += 1
                        results["draw" if lab == 0.5 else
                                ("white" if g["result"] == "1-0" else "black")] += 1
    print(f"партий: {n_games}, позиций: {n_pos}, на партию: {n_pos / max(n_games, 1):.1f}")
    print(f"середина (ph>=7): {bands['middle']}, эндшпиль (ph<=6): {bands['endgame']}")
    print(f"повторов пропущено: {n_dup}")
    print(f"результаты партий: {dict(results)}")


if __name__ == "__main__":
    main()
