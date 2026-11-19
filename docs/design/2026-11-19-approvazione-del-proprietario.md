# Approvazione scritta del proprietario (19 novembre 2026)

Frase del proprietario, testuale: «Approvo il piano e l'elenco A del 19 novembre».

## Cosa è stato approvato
- Il piano del run: `docs/design/2026-10-11-piano-run-v3.md`, SHA-256 `ca34731f0b8b7aa8103b092fd4ea2f99b6c0ac0e16a0e1f6c194c496870b4cc6` (il contenuto committato). Da qui non si modifica più.
- L'elenco A delle impronte: `docs/design/2026-11-elenco-A-impronte.json`, SHA-256 del file `90545aab25aca09e20f47bfc6fd758011d7045619e4dd939bc0cc3424c9ca646`;
  generato il 2026-11-19 dal commit del codice `4441646a4137c998645dff70c1a2a4dcfb987552`; 127 file in 7 gruppi; tre immagini registrate
  (`1c2bff07ed71`, `2a4b5e938f04`, `5957cd592929`).
- Le scelte segnate «di Claude» nel piano e quelle elencate in `docs/notes/2026-11-19-riepilogo-per-l-approvazione.md`, insieme ai limiti noti scritti lì.

## Controlli fatti prima della firma
- `elenco_a verifica` e `verifica-immagini --a-fondo`: nessuna differenza. Contenuto uguale a quello provato dal micro giro del 18 novembre
  (stessi gruppi, stesse immagini).
- Impronta delle istruzioni del revisore ricalcolata dopo l'ultima modifica del piano: `e5940b4da3a44aff60bcc0b66f97d6415ace0b8a413efcb0fea33c94c94e936f`, invariata.
- Suite di test: 1502 passati, 8 saltati. Prova su scala dell'analisi e micro giro: esiti in `docs/research/2026-11-18-prova-analisi-su-scala/` e `docs/research/2026-11-18-micro-giro/`.
- Scansione di chiavi nei file tracciati e nella storia che uscirebbe con il push: nessuna corrispondenza.

## Stato
Approvato, NON ancora pubblicato. Il push su `origin` (la prova di data) richiede un sì separato del proprietario.
