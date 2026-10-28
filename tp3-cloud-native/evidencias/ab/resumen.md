### Métricas (objetivo TP2: p95 <= 300 ms, p99 <= 800 ms, sin fallos)

| Escenario | Conc. | Completadas | Fallidas | (Conn/Recv/Len/Exc) | No-2xx | Req/s | Media ms | p50 | p95 | p99 | Máx ms | SLO TP2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_moderada_c100 | 100 | 5000 | 0 | - | 0 | 1383.99 | 72.3 | 68 | 93 | 104 | 157 | CUMPLE |
| B_alta_c500 | 500 | 10000 | 0 | - | 0 | 1364.34 | 366.5 | 338 | 426 | 430 | 543 | NO CUMPLE |
| C_extrema_c1000 | 1000 | 10000 | 0 | - | 0 | 1430.62 | 699.0 | 676 | 789 | 819 | 830 | NO CUMPLE |
| D_extrema_c2000 | 2000 | 20000 | 0 | - | 0 | 1279.55 | 1563.1 | 1438 | 1627 | 1680 | 2119 | NO CUMPLE |
| E_cpu_c100 | 100 | 5000 | 0 | - | 2966 | 325.49 | 307.2 | 22 | 2003 | 2418 | 6004 | NO CUMPLE |
| E_cpu_c1000 | 1000 | 5000 | 0 | - | 4456 | 660.17 | 1514.8 | 566 | 4442 | 5367 | 7418 | NO CUMPLE |
| F_1replica_c1000 | 1000 | 10000 | 0 | - | 0 | 1217.62 | 821.3 | 749 | 1751 | 1976 | 2584 | NO CUMPLE |
| F_1replica_cpu_c100 | 100 | 5000 | 0 | - | 3018 | 67.25 | 1487.1 | 2002 | 3066 | 3078 | 3089 | NO CUMPLE |
| G_post_envios_c100 | 100 | 5000 | 0 | - | 33 | 1216.83 | 82.2 | 73 | 118 | 134 | 174 | NO CUMPLE |

### Diagnóstico: ¿qué se saturó primero?

| Escenario | CPU máx réplica (%) | CPU máx nginx (%) | Conexiones activas máx en nginx | Errores nuevos en log de nginx |
|---|---|---|---|---|
| A_moderada_c100 | 25 | 40 | 22 | 0 |
| B_alta_c500 | 17 | 42 | 278 | 0 |
| C_extrema_c1000 | 17 | 50 | 86 | 0 |
| D_extrema_c2000 | 12 | 45 | 1929 | 0 |
| E_cpu_c100 | 54 | 21 | 101 | 3316 |
| E_cpu_c1000 | 55 | 37 | 1001 | 6453 |
| F_1replica_c1000 | 54 | 43 | 875 | 0 |
| F_1replica_cpu_c100 | 55 | 6 | 101 | 3019 |
| G_post_envios_c100 | 26 | 46 | 101 | 33 |

(Con `cpus: 0.50` una réplica al límite muestra ~50 % en docker stats.)

### Escalabilidad: 3 réplicas vs 1 réplica

| Prueba | Req/s 1 réplica | Req/s 3 réplicas | Speedup | Eficiencia (ideal 100 %) | p99 1 réplica | p99 3 réplicas |
|---|---|---|---|---|---|---|
| GET / (c=1000) | 1217.62 | 1430.62 | 1.17x | 39 % | 1976 | 819 |
| GET /work (c=100) | 67.25 | 325.49 | 4.84x | 161 % | 3078 | 2418 |
