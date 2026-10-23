#!/usr/bin/env bash
# Ejecuta todos los escenarios de carga y guarda los resultados en results/
# Requisitos: entorno levantado (docker-compose up -d) y Apache Benchmark (ab):
#   Ubuntu/Debian/WSL: sudo apt install apache2-utils     macOS: ya viene instalado
# Recomendación: cerrar aplicaciones pesadas durante la prueba (el generador de carga
# comparte CPU con los contenedores).
set -uo pipefail

URL="${URL:-http://localhost/}"
OUT="results"
mkdir -p "$OUT"
ulimit -n 65535 2>/dev/null || ulimit -n 4096 2>/dev/null || true

if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi

nginx_errors() {  # cantidad de líneas error/alert/crit en el log de NGINX
  $DC logs nginx 2>&1 | grep -cE "\[(error|alert|crit)\]"; true
}

monitor_start() {  # muestrea CPU/RAM de cada contenedor y conexiones activas de NGINX
  (
    while true; do
      ts=$(date +%T)
      docker stats --no-stream --format "$ts,{{.Name}},{{.CPUPerc}},{{.MemUsage}}" \
        >> "$OUT/stats_$1.csv" 2>/dev/null
      echo "$ts $(curl -s --max-time 1 http://localhost/nginx-status | tr '\n' ' ')" >> "$OUT/nginx_status_$1.txt"
    done
  ) &
  MON_PID=$!
}
monitor_stop() { kill "$MON_PID" 2>/dev/null; wait "$MON_PID" 2>/dev/null; true; }

run() {  # run <nombre> <peticiones> <concurrencia> <url> [args extra de ab]
  local name="$1" n="$2" c="$3" target="$4"; shift 4
  echo ">>> $name  (n=$n, c=$c)  $target"
  rm -f "$OUT/stats_$name.csv" "$OUT/nginx_status_$name.txt"
  local e0 e1; e0=$(nginx_errors)
  monitor_start "$name"
  ab -l -n "$n" -c "$c" -s 30 "$@" "$target" > "$OUT/$name.txt" 2>&1
  monitor_stop
  e1=$(nginx_errors)
  echo $((e1 - e0)) > "$OUT/nginx_errors_$name.txt"
  grep -E "Failed requests|Non-2xx|Requests per second|Time per request" "$OUT/$name.txt" || tail -n 3 "$OUT/$name.txt"
  echo "    errores nuevos en NGINX: $((e1 - e0))"; echo
  sleep 8   # enfriamiento entre pruebas
}

echo "=== Calentamiento ==="
ab -l -n 500 -c 10 "$URL" > /dev/null 2>&1

echo "=== A: concurrencia moderada ==="
run A_moderada_c100      5000   100  "$URL"
echo "=== B: concurrencia alta ==="
run B_alta_c500          10000  500  "$URL"
echo "=== C: concurrencia extrema (10.000 peticiones, objetivo del TP2) ==="
run C_extrema_c1000      10000  1000 "$URL"
run D_extrema_c2000      20000  2000 "$URL"
echo "=== E: saturación de CPU (endpoint /work) ==="
run E_cpu_c100           5000   100  "${URL}work?n=300000"
run E_cpu_c1000          5000   1000 "${URL}work?n=300000"
echo "=== G: POST /envios/crear (endpoint clave del TP2) ==="
echo '{"destinatario":"test","origen":"AR","destino":"CL"}' > "$OUT/body.json"
run G_post_envios_c100   5000   100  "${URL}envios/crear" -p "$OUT/body.json" -T application/json \
    -H "Idempotency-Key: 7b1f3c9e-52e4-4d8e-9a77-0c4e1f2b3a10"

echo "=== F: línea base con 1 sola réplica (para medir escalabilidad) ==="
$DC up -d --scale api=1 --no-recreate >/dev/null 2>&1
$DC restart nginx >/dev/null 2>&1; sleep 10
run F_1replica_c1000     10000  1000 "$URL"
run F_1replica_cpu_c100  5000   100  "${URL}work?n=300000"

echo "=== Restaurando 3 réplicas ==="
$DC up -d --scale api=3 --no-recreate >/dev/null 2>&1
$DC restart nginx >/dev/null 2>&1; sleep 10

echo "=== Resumen ==="
python3 scripts/parse_ab.py "$OUT" | tee "$OUT/resumen.md"
