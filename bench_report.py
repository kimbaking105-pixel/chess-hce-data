import json, sys, statistics as st
for fn in sys.argv[1:]:
    G=[json.loads(l) for l in open(fn)]
    if not G: print(fn,"пусто"); continue
    W=[g["wall_s"] for g in G]; P=[g["plies"] for g in G]
    d=sum(g["result"]=="1/2-1/2" for g in G)
    print(f"{fn}: партий {len(G)}, среднее wall {st.mean(W):.1f} с (медиана {st.median(W):.1f}), "
          f"полуходов {st.mean(P):.0f}, ничьих {d/len(G):.0%}, причины {sorted(set(g['reason'] for g in G))}")
