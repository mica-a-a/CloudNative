# Evidencias (corrida en macOS)

| Archivo | Qué demuestra |
|---|---|
| `01_balanceo.png` | `docker compose ps` (3 réplicas healthy + nginx) y reparto entre réplicas (hostnames y `upstream=` en el log) |
| `02_A_moderada_c100.jpeg` | Escenario A: `ab -l -n 5000 -c 100 http://localhost/` |
| `03_resiliencia.jpeg` | Con una réplica detenida responden solo las 2 vivas; restauración con `--scale api=3` |
| `04_C_extrema_c1000.jpeg` | Escenario C: `ab -l -n 10000 -c 1000 http://localhost/` |
| `05_G_post_envios_c100.jpeg` | Escenario G: POST `/envios/crear` con `Idempotency-Key`, 5.000 pedidos, 100 concurrentes |
| `06_docker_stats.jpeg` | `docker stats` bajo carga (NGINX vs réplicas) |
| `ab/` | Salidas crudas de `ab` y `resumen.md` generados por `scripts/run_benchmarks.sh` |
