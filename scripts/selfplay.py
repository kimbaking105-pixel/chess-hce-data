#!/usr/bin/env python3
"""Самоигра двух UCI-движков с контролем base+inc (по умолчанию 5 с + 0.1 с).

Пишет JSONL: одна строка на партию (результат, ходы, стартовая позиция).
Извлечение позиций делает extract.py.
Стартовые позиции — случайные открытия (по seed). Для каждой стартовой позиции
сыграны две партии с обменом цветов (баланс меток).
"""
import argparse
import json
import os
import random
import time

import chess
import chess.engine


def random_opening(rng, plies=8):
    """Случайная позиция после `plies` полуходов, без мата/пата и без шаха стороне хода."""
    while True:
        b = chess.Board()
        ok = True
        for _ in range(plies):
            moves = list(b.legal_moves)
            if not moves or b.is_game_over():
                ok = False
                break
            b.push(rng.choice(moves))
        if ok and not b.is_game_over() and not b.is_check():
            return b.fen()


def play_game(eA, eB, start_fen, a_is_white, base, inc, max_plies=300):
    t_start = time.time()
    board = chess.Board(start_fen)
    clocks = {chess.WHITE: base, chess.BLACK: base}
    engines = {
        chess.WHITE: eA if a_is_white else eB,
        chess.BLACK: eB if a_is_white else eA,
    }
    moves = []
    while not board.is_game_over(claim_draw=True) and len(board.move_stack) < max_plies:
        side = board.turn
        lim = chess.engine.Limit(
            white_clock=clocks[chess.WHITE],
            black_clock=clocks[chess.BLACK],
            white_inc=inc,
            black_inc=inc,
        )
        t0 = time.time()
        res = engines[side].play(board, lim)
        spent = time.time() - t0
        clocks[side] = clocks[side] - spent + inc
        if clocks[side] <= 0:
            # проигрыш по времени стороны, которая ходила
            return {
                "result": "0-1" if side == chess.WHITE else "1-0",
                "reason": "time",
                "moves": [m.uci() for m in moves],
                "plies": len(board.move_stack),
                "wall_s": round(time.time() - t_start, 2),
            }
        if res.move is None:
            return {
                "result": "1/2-1/2",
                "reason": "nomove",
                "moves": [m.uci() for m in moves],
                "plies": len(board.move_stack),
                "wall_s": round(time.time() - t_start, 2),
            }
        moves.append(res.move)
        board.push(res.move)

    if board.is_game_over(claim_draw=True):
        result = board.result(claim_draw=True)
        reason = "mate" if board.is_checkmate() else "draw"
    else:
        result, reason = "1/2-1/2", "maxplies"
    return {
        "result": result,
        "reason": reason,
        "moves": [m.uci() for m in moves],
        "plies": len(board.move_stack),
        "elapsed_white": round(base - clocks[chess.WHITE], 2),
        "wall_s": round(time.time() - t_start, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="путь к движку A")
    ap.add_argument("--b", required=True, help="путь к движку B")
    ap.add_argument("--pairs", type=int, required=True, help="число пар (каждая пара = 2 партии)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--base", type=float, default=5.0)
    ap.add_argument("--inc", type=float, default=0.1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    eA = chess.engine.SimpleEngine.popen_uci(args.a)
    eB = chess.engine.SimpleEngine.popen_uci(args.b)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    try:
        with open(args.out, "a") as f:
            for p in range(args.pairs):
                # 8 или 9 полуходов наугад: иначе после чётного числа полуходов всегда ходят белые,
                # и преимущество хода уходит в перекос по цветам
                start = random_opening(rng, plies=rng.choice([8, 9]))
                for a_white in (True, False):
                    gid = f"{args.tag}_s{args.seed}_p{p}_{'A' if a_white else 'B'}"
                    g = play_game(eA, eB, start, a_white, args.base, args.inc)
                    g.update({
                        "game_id": gid,
                        "a_is_white": a_white,
                        "engine_a": os.path.basename(args.a),
                        "engine_b": os.path.basename(args.b),
                        "start_fen": start,
                        "base": args.base,
                        "inc": args.inc,
                    })
                    f.write(json.dumps(g) + "\n")
                    f.flush()
    finally:
        eA.quit()
        eB.quit()


if __name__ == "__main__":
    main()
