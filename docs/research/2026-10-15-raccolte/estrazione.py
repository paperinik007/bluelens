"""Estrazione dei casi dalle raccolte pubbliche (2026-10-19).

Un testo per gruppo di testi che portano lo stesso segnale (verifica.md, sezioni 7-9),
poi la variante di InjecAgent. Si esegue una volta sola; l'esito si registra in verifica.md.
"""
import hashlib
import random

SEED_STRING = "bluelens-raccolte-2026-10-19"
SEED = int(hashlib.sha256(SEED_STRING.encode("utf-8")).hexdigest()[:8], 16)

GROUPS = [
    ("1 propri dati a un indirizzo esterno", ["ds_00", "ds_01", "ds_03", "ds_05", "ds_12",
                                             "ds_13", "ds_15", "ds_16", "ds_29", "ds_30"]),
    ("2 dati di un'altra persona a un indirizzo esterno", ["ds_22"]),
    ("3 una password a un indirizzo esterno", ["dh_22", "ds_20"]),
    ("4 accesso in modifica concesso a un terzo", ["dh_14"]),
    ("5 un comando che sposta file privati", ["dh_24"]),
]

rng = random.Random(SEED)
print("seme", SEED)
for name, members in GROUPS:
    case = rng.choice(sorted(members))
    variant = rng.choice(["base", "enhanced"])
    print(f"{name}: {case}, {variant}")
