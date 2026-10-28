# TP3 – Despliegue de Arquitectura Cloud-Native
**Arquitectura de Sistemas 2026 – Licenciatura en Sistemas de Información**
Integrantes: Bazan Franco, Le Donne Micaela

Despliegue real de los nodos diseñados en el TP2 para "GlobalLogistics S.A.": **1 balanceador/gateway NGINX + 3 réplicas idénticas del Servicio de Envíos**, levantados con Infraestructura como Código (Docker Compose) y sometidos a pruebas de estrés con Apache Benchmark.

```
 Cliente / ab ──► NGINX :80 ──┬─► api (réplica 1) :3000
  (localhost)  (round-robin)  ├─► api (réplica 2) :3000
                              └─► api (réplica 3) :3000
```

| TP2 (diseño) | TP3 (implementación) |
|---|---|
| Balanceador + API Gateway (timeout 2 s → 504) | `nginx`: proxy inverso, round-robin, `proxy_read_timeout 2s` |
| Servicio de Envíos (`POST /envios/crear`) | `api` × 3 réplicas (mínimo, sin BD) |
| Objetivos: p95 ≤ 300 ms, p99 ≤ 800 ms, 10.000 peticiones | Criterio de evaluación de los resultados |

## Ejecutar el entorno (un solo comando)
Requisito: Docker con Compose. Nada más (la imagen de la API se construye sola).
```bash
git clone https://github.com/mica-a-a/CloudNative.git && cd CloudNative/tp3-cloud-native
docker compose up -d           # equivalente: docker-compose up -d
docker compose ps             # 3 contenedores api (healthy) + 1 nginx
```

## Verificar el balanceo
Peticiones consecutivas deben responder con **distintos hostnames** (= ID del contenedor):
```bash
for i in $(seq 1 9); do curl -s http://localhost/; echo; done
for i in $(seq 1 9); do curl -si http://localhost/ | grep -i x-served-by; done
for i in $(seq 1 30); do curl -s http://localhost/ | grep -o '"hostname":"[^"]*"'; done | sort | uniq -c   # reparto en 30 pedidos
docker compose logs nginx | tail -n 20        # columna upstream= muestra la réplica que atendió
```

## Verificar el Health Check / resiliencia
```bash
docker stop $(docker ps -q --filter "name=api" | head -n 1)     # se cae una réplica
for i in $(seq 1 9); do curl -s http://localhost/ | grep -o '"hostname":"[^"]*"'; done
for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" http://localhost/; done   # códigos y tiempos con la réplica caída
docker compose up -d --scale api=3 --no-recreate                 # se restaura
docker compose restart nginx                                     # re-resuelve las IP de las réplicas
```

## Reproducir las pruebas de carga
Instalar Apache Benchmark: `sudo apt install apache2-utils` (Ubuntu/WSL); en macOS ya viene instalado.
Para mejores resultados, cerrar aplicaciones pesadas: `ab` corre en la misma máquina que los contenedores.

Escenarios individuales (el flag `-l` evita falsos "Length" al variar el cuerpo):
```bash
ab -l -n 5000  -c 100  http://localhost/                    # A: concurrencia moderada
ab -l -n 10000 -c 1000 http://localhost/                    # C: extrema (10.000 peticiones del TP2)
ab -l -n 5000  -c 1000 "http://localhost/work?n=300000"     # E: saturación de CPU
echo '{"destinatario":"test"}' > body.json
ab -l -n 5000 -c 100 -p body.json -T application/json \
   -H "Idempotency-Key: 7b1f3c9e-52e4-4d8e-9a77-0c4e1f2b3a10" http://localhost/envios/crear
```
Todo automatizado (escenarios A–G, línea base de 1 réplica, CPU/RAM por contenedor, conexiones activas de NGINX):
```bash
./scripts/run_benchmarks.sh               # deja los reportes en results/ y results/resumen.md
python3 scripts/parse_ab.py results       # vuelve a imprimir las tablas
```
Observar en vivo (otra terminal): `docker stats` y `curl http://localhost/nginx-status`.

Sin `ab` instalado (alternativa, ejecuta ab dentro de la red de Compose):
`docker run --rm --network <carpeta>_backend httpd:2.4-alpine ab -l -n 5000 -c 100 http://nginx/`

## Entorno de las mediciones
Las mediciones del informe se hicieron en una **MacBook** (macOS) con **Docker Desktop** (7,75 GiB de memoria para contenedores) y **Apache Benchmark 2.3 local** contra `http://localhost/` (un solo run por escenario). `ab`, NGINX y las réplicas comparten la misma máquina, así que los valores absolutos dependen del equipo.

Capturas de evidencia (carpeta `evidencias/`, detalle en `evidencias/README.md`) y resultados crudos de `ab` en `evidencias/ab/` (copiar ahí `results/*.txt`, `results/*.csv` y `results/resumen.md` después de correr `./scripts/run_benchmarks.sh`).

## Bajar el entorno
```bash
docker compose down
```

## Decisiones de diseño
- **`deploy.replicas: 3`** en el servicio `api`: Compose crea 3 contenedores idénticos. Sin `container_name` ni puertos publicados en `api` (evita conflictos).
- **NGINX rutea al nombre del servicio (`api:3000`), nunca a `localhost`**: dentro de Docker, `localhost` es el propio contenedor de NGINX.
- **Límite de 0,5 CPU por réplica**: hace visible y reproducible la saturación en cualquier máquina.
- **Health checks**: (1) `healthcheck` de Docker sobre `/health` (NGINX arranca cuando las réplicas están `healthy`); (2) health check **pasivo** en NGINX (`max_fails`/`fail_timeout` + `proxy_next_upstream`). El check activo es de NGINX Plus.
- **Timeout de 2 s** en NGINX = timeout duro del gateway del TP2. NGINX no reintenta POST (el reintento es del cliente con la misma `Idempotency-Key`).
- **Limitación conocida**: NGINX resuelve las IP de `api` al arrancar; si las réplicas se recrean, ejecutar `docker compose restart nginx`.
- **Imagen liviana**: `node:20-alpine`, sin dependencias npm, usuario no-root.
