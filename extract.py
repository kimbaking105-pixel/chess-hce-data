#!/usr/bin/env python3
"""Извлечение тихих позиций из JSONL-партий (вывод selfplay.py).

Фильтр тишины (фиксирован заранее, одинаков для всех моделей):
  - сторона, которая ходит, не под шахом;
  - нет легального взятия (включая en passant) и нет превращения;
  - позиция не терминальная;
  - номер полухода от 10 до (len(moves) - 10), т.е. без дебютной и концовочной части.
Метка: результат партии с точки зрения стороны, которая ходит (1 / 0.5 / 0).
Ограничение: не более --cap позиций на одну партию (чтобы длинные партии не доминировали).
Выход: JSONL-строки {game_id, ply, fen, stm, label} + фиксированный seed.
Оценки движков в метках не используются.
"""
import argparse
import json
import random

import chess


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=30)
    ap.add_argument("--min_ply", type=int, default=10)
    ap.add_argument("--tail", type=int, default=10)
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    n_games = n_pos = 0
    stats = {"white": 0, "black": 0, "draw": 0}
    with open(args.out, "w") as out:
        for path in args.inp:
            for line in open(path):
                g = json.loads(line)
                n_games += 1
                start = g.get("start_fen", chess.STARTING_FEN)
                moves = g["moves"]
                board = chess.Board(start)
                cands = []
                for i, uci in enumerate(moves):
                    if args.min_ply <= i < len(moves) - args.tail:
                        if quiet(board):
                            cands.append((i, board.fen(), board.turn))
                    board.push(chess.Move.from_uci(uci))
                if len(cands) > args.cap:
                    cands = rng.sample(cands, args.cap)
                for ply, fen, stm in cands:
                    lab = label_for(g["result"], stm)
                    if lab is None:
                        continue
                    out.write(json.dumps({
                        "game_id": g["game_id"], "ply": ply, "fen": fen,
                        "stm": "w" if stm == chess.WHITE else "b", "label": lab,
                    }) + "\n")
                    n_pos += 1
                    stats["draw" if lab == 0.5 else ("white" if g["result"] == "1-0" else "black")] += 1
    print(f"партий: {n_games}, тихих позиций: {n_pos}, на партию: {n_pos / max(n_games, 1):.1f}")
    print(f"результаты партий: {stats}")


if __name__ == "__main__":
    main()
