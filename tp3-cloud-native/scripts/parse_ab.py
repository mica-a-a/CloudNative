#!/usr/bin/env python3
"""Resume los reportes de Apache Benchmark guardados en results/.
Uso: python3 scripts/parse_ab.py [carpeta]      (por defecto: results)
Imprime tablas Markdown: métricas, diagnóstico (CPU / conexiones NGINX) y escalabilidad."""
import os, re, sys

SLO_P95, SLO_P99 = 300, 800   # objetivos de calidad definidos en el TP2 (ms)


def grab(pattern, text, cast=float):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else None


def parse_ab(path):
    t = open(path, encoding="utf-8", errors="ignore").read()
    r = {"name": os.path.basename(path)[:-4]}
    if "Requests per second" not in t:                       # ab abortó antes de terminar
        msg = re.search(r"(apr_\w+\(\d+\)[^\n]*|[^\n]*Connection reset[^\n]*|[^\n]*timed out[^\n]*)", t)
        r["abortado"] = msg.group(1).strip() if msg else "sin reporte"
        return r
    r.update(
        conc=grab(r"Concurrency Level:\s+(\d+)", t, int),
        done=grab(r"Complete requests:\s+(\d+)", t, int),
        failed=grab(r"Failed requests:\s+(\d+)", t, int),
        non2xx=grab(r"Non-2xx responses:\s+(\d+)", t, int) or 0,
        rps=grab(r"Requests per second:\s+([\d.]+)", t),
        mean=grab(r"Time per request:\s+([\d.]+) \[ms\] \(mean\)", t),
        p50=grab(r"\s50%\s+(\d+)", t), p95=grab(r"\s95%\s+(\d+)", t),
        p99=grab(r"\s99%\s+(\d+)", t), mx=grab(r"\s100%\s+(\d+)", t),
    )
    d = re.search(r"Connect: (\d+), Receive: (\d+), Length: (\d+), Exceptions: (\d+)", t)
    r["detalle"] = "C%s/R%s/L%s/E%s" % d.groups() if d else "-"
    ok = r["p95"] <= SLO_P95 and r["p99"] <= SLO_P99 and r["failed"] == 0 and r["non2xx"] == 0
    r["slo"] = "CUMPLE" if ok else "NO CUMPLE"
    return r


def diag(folder, name):
    """CPU máx de réplicas y de nginx, conexiones activas máx y errores de NGINX."""
    cpu_api = cpu_ng = 0.0
    p = os.path.join(folder, f"stats_{name}.csv")
    if os.path.exists(p):
        for line in open(p, errors="ignore"):
            f = line.strip().split(",")
            if len(f) < 3:
                continue
            try:
                v = float(f[2].replace("%", ""))
            except ValueError:
                continue
            if re.search(r"[-_]api[-_]\d+$", f[1]):
                cpu_api = max(cpu_api, v)
            elif re.search(r"[-_]nginx[-_]\d+$", f[1]):
                cpu_ng = max(cpu_ng, v)
    act = 0
    p = os.path.join(folder, f"nginx_status_{name}.txt")
    if os.path.exists(p):
        for line in open(p, errors="ignore"):
            m = re.search(r"Active connections:\s+(\d+)", line)
            if m:
                act = max(act, int(m.group(1)))
    errs = "-"
    p = os.path.join(folder, f"nginx_errors_{name}.txt")
    if os.path.exists(p):
        errs = open(p).read().strip()
    return cpu_api, cpu_ng, act, errs


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "results"
    files = sorted(f for f in os.listdir(folder)
                   if f.endswith(".txt") and not f.startswith(("stats_", "nginx_")))
    res = {}
    for f in files:
        r = parse_ab(os.path.join(folder, f))
        res[r["name"]] = r

    print(f"### Métricas (objetivo TP2: p95 <= {SLO_P95} ms, p99 <= {SLO_P99} ms, sin fallos)\n")
    print("| Escenario | Conc. | Completadas | Fallidas | (Conn/Recv/Len/Exc) | No-2xx | Req/s "
          "| Media ms | p50 | p95 | p99 | Máx ms | SLO TP2 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for n, r in res.items():
        if "abortado" in r:
            print(f"| {n} | - | - | - | - | - | - | - | - | - | - | - "
                  f"| ABORTADO: {r['abortado']} |")
        else:
            print(f"| {n} | {r['conc']} | {r['done']} | {r['failed']} | {r['detalle']} "
                  f"| {r['non2xx']} | {r['rps']} | {r['mean']:.1f} | {r['p50']:.0f} | {r['p95']:.0f} "
                  f"| {r['p99']:.0f} | {r['mx']:.0f} | {r['slo']} |")

    print("\n### Diagnóstico: ¿qué se saturó primero?\n")
    print("| Escenario | CPU máx réplica (%) | CPU máx nginx (%) "
          "| Conexiones activas máx en nginx | Errores nuevos en log de nginx |")
    print("|---|---|---|---|---|")
    for n in res:
        a, g, act, e = diag(folder, n)
        print(f"| {n} | {a:.0f} | {g:.0f} | {act} | {e} |")
    print("\n(Con `cpus: 0.50` una réplica al límite muestra ~50 % en docker stats.)")

    pairs = [("C_extrema_c1000", "F_1replica_c1000", "GET / (c=1000)"),
             ("E_cpu_c100", "F_1replica_cpu_c100", "GET /work (c=100)")]
    print("\n### Escalabilidad: 3 réplicas vs 1 réplica\n")
    print("| Prueba | Req/s 1 réplica | Req/s 3 réplicas | Speedup "
          "| Eficiencia (ideal 100 %) | p99 1 réplica | p99 3 réplicas |")
    print("|---|---|---|---|---|---|---|")
    for three, one, label in pairs:
        a, b = res.get(three), res.get(one)
        if a and b and "abortado" not in a and "abortado" not in b and b["rps"]:
            sp = a["rps"] / b["rps"]
            print(f"| {label} | {b['rps']} | {a['rps']} | {sp:.2f}x | {sp / 3 * 100:.0f} % "
                  f"| {b['p99']:.0f} | {a['p99']:.0f} |")
        else:
            print(f"| {label} | (faltan datos) | | | | | |")


if __name__ == "__main__":
    main()
