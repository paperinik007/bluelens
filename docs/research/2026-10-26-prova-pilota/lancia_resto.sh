#!/bin/sh
# Resto della prova pilota (2026-10-27): un giudice per volta, inglese poi italiano; tetto 2,5 dollari nel registro.
# Uso: sh lancia_resto.sh alignmentcheck|aidr   (dalla cartella del repo; log in lancia_resto_<giudice>.log)
P=docs/research/2026-10-26-prova-pilota
export PYTHONPATH=src PYTHONUNBUFFERED=1
J=$1
COMMON="--max-consecutive-failures ${MAXFAIL:-3} --ledger $P/gasto.json --ceiling 2.5 --compose-file docker-compose.yml --compose-file $P/docker-compose.pilot.yml --env-file .env.aidr"
python -m toy_agent.judge_sessions --judge $J --sessions $P/sessioni-en --repeats 5 --out $P/verdetti-en $COMMON
python -m toy_agent.judge_sessions --judge $J --sessions $P/sessioni-originali --ids $P/ids-prova-lingua.txt --repeats 3 --out $P/verdetti-it $COMMON
