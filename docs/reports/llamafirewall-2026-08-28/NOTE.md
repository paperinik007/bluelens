# Nota sulla correzione dell'hash di provenance (2026-09-10)

Il repo ha subito due riscritture di storia dopo questo run: la purga dei
file di note interne del 2026-09-04 (§10 di `posizionamento.md`) e una
seconda riscrittura del 2026-09-10 (sostituzione dell'email dell'autore
nei metadati dei commit, prima della pubblicazione del repo). Entrambe
cambiano l'hash di ogni commit.

`measurer_commit` in `provenance.json` è stato aggiornato da
`7d726bef162e90890f50b93f55614739bdfc32c2` a
`250f64e8edc3d72a0a5531cd0b5557c7f29481ab` — stesso commit (stesso
messaggio, stessa data di autore), solo ri-calcolato dopo le due
riscritture. Nessuna differenza di codice o contenuto.
