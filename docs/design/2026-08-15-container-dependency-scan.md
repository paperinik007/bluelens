# Scan dipendenze del container di controllo (Trivy)

Verifica richiesta dal design doc, sezione "Container di controllo" — audit di
sicurezza preventivo prima di usare il container come confine di contenimento.

## Comando

    trivy image --severity CRITICAL --exit-code 1 <control-image-tag>
    trivy image --severity CRITICAL --exit-code 1 <egress-proxy-image-tag>

Eseguito tramite l'immagine Docker ufficiale di Trivy (Trivy non è installato
sulla macchina host), con il socket Docker montato:

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ \
      aquasec/trivy image --severity CRITICAL --exit-code 1 <image-tag>

## Risultato

- Immagine `egress-proxy` (digest:
  `sha256:0772113681c56c81b4eb4c90d50f6f55bcf52c0f8a9d8fad0315c44a629bbabd`,
  build 2026-08-15T05:51:08Z): **0 vulnerabilità CRITICAL**, scansionata il
  2026-08-15. Exit code: 0.

- Immagine `control` (digest:
  `sha256:6c4087ddd3a1766661f7d608ed1d6b0e4bb490601ec341f13d7ac432d81afa94`,
  build 2026-08-15T17:44:34Z): **4 vulnerabilità CRITICAL residue**
  (originariamente 16 — vedi sezione "Note" per la riduzione), tutte sul
  pacchetto `perl-base`, scansionata il 2026-08-15. Exit code: 1.

  **Questo è un rischio accettato in modo esplicito e motivato dal titolare
  del progetto dopo discussione (2026-08-15), non un gate passato in
  silenzio.** Nessuna delle 4 CVE ha una fix disponibile — né da Debian, né
  altrove — a questa data. Il comando `trivy ... --exit-code 1` continuerà a
  restituire 1 finché Debian non rilascia una patch per `perl-base`
  (verificabile con `apt-cache policy perl-base` dentro l'immagine base:
  `Installed` e `Candidate` sono identici, 5.40.1-6, nessun upgrade
  disponibile). Questo file documenta perché il team ha deciso di procedere
  comunque, quali controlli compensativi sono in atto, e cosa cambierebbe la
  decisione (una fix Debian).

### Le 4 CVE residue

| CVE | Descrizione | Perché non è raggiungibile da questo progetto | Nota mitigante specifica |
|---|---|---|---|
| CVE-2026-13221 | Perl produce risultati di match regex silenziosamente errati compilando un'alternanza di oltre 65535 rami a stringa fissa in un trie. | Richiede una regex controllata dall'attaccante con un numero enorme di alternative letterali, eseguita da perl. | — |
| CVE-2026-8376 | Heap buffer overflow compilando una regex a stringa fissa ripetuta — **solo build a 32 bit**. | Come sopra, e comunque non applicabile: l'immagine `control` è amd64. | Immagine `control` è amd64, non 32-bit — CVE non applicabile a questo target di build. |
| CVE-2026-57433 | Overflow di intero con segno nel modulo `Storable` deserializzando un record `SX_HOOK` malformato (`retrieve_hook_common`). | Richiede una chiamata a `Storable::thaw`/`retrieve` su dati serializzati non fidati. | — |
| CVE-2026-42496 | `Archive::Tar` di Perl segue target di symlink/hardlink controllati dall'attaccante durante l'estrazione, uscendo dalla directory di estrazione. Fix upstream disponibile in Archive::Tar 3.08. | Richiede l'estrazione di un tar malevolo tramite `Archive::Tar`. | Debian ha marcato questa CVE **"postponed"** sia per trixie che per bookworm nel proprio Security Tracker, con motivazione "Minor issue; wait for regressions upstream sorted out" — Debian stesso non la considera prioritaria da backportare a breve. |

**Filo comune alle 4 CVE**: tutte richiedono che Perl esegua effettivamente
input controllato dall'attaccante (una regex malevola, un payload `Storable`
malevolo, o un tar malevolo con symlink). **Nessun codice di questo
progetto — `entrypoint.sh`, `toy_agent`, il codice vendor `aidr` — invoca mai
perl su alcun percorso.** Verificato con:

    grep -ri perl <root del repo>

L'unico risultato reale in tutto il repo (escludendo questo stesso documento
e il report di Task 4) è un falso positivo per substring in
`tests/toy_agent/test_tools.py` (`properly` contiene "perl" come substring).
Nessun invocazione reale di `perl` in `docker/control/entrypoint.sh`, in
`src/toy_agent/`, né in alcun punto del Dockerfile stesso.

## Immagine agent

Immagine `agentic-security-audits-agent` (digest:
`sha256:31fcb564f78e1fffa94f1e06e443a8ed2f0002589147959ea1b6c5eca9c4cc1d`,
build 2026-08-16T15:28:11Z), Gap 9 — split del container di controllo in
`agent` (solo `toy_agent`) e `detector` (Task 3, vedi sezione "Immagine
detector" più sotto). Scansionata il 2026-08-16 con lo stesso comando dockerizzato
(Trivy non installato come binario sulla macchina host):

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ \
      aquasec/trivy image --severity CRITICAL --exit-code 1 agentic-security-audits-agent

**4 vulnerabilità CRITICAL residue**, tutte sul pacchetto `perl-base`
(`CVE-2026-13221`, `CVE-2026-42496`, `CVE-2026-57433`, `CVE-2026-8376`) —
esattamente le stesse 4 CVE già documentate sopra per `control`, stessa causa
radice: `perl-base` è parte del set essenziale Debian e resta presente in
qualunque immagine `python:3.11-slim`, indipendentemente dal Dockerfile.
Exit code: 1. Nessuna CVE CRITICAL aggiuntiva/diversa rispetto a `control`.

Questa immagine `agent` (`docker/agent/Dockerfile`) applica lo stesso
controllo compensativo già in atto per `control` — `chmod a-x /usr/bin/perl
/usr/bin/perl5.40.1` come ultimo passo di build — e ricade sotto la
**stessa eccezione già accettata dal titolare del progetto (2026-08-15)**:
nessuna delle 4 CVE ha una fix disponibile a questa data, nessun codice di
questa immagine (`entrypoint.sh`, `toy_agent`) invoca mai perl su alcun
percorso, e l'immagine `agent` non ha nemmeno lo stage di build con `git`
(non installato affatto in questo Dockerfile — `toy_agent` non ha
dipendenze vendor da clonare), quindi la superficie è anzi più ridotta di
quella di `control`. Non è una nuova decisione di rischio da discutere: è la
stessa eccezione, riapplicata a una seconda immagine che condivide la stessa
causa non risolvibile lato Debian.

## Immagine detector

Immagine `agentic-security-audits-detector` (digest:
`sha256:7ffd08d905e755c02734ba79c88ac07228ffcedc19246976c1fb61446e3d09ad`,
build 2026-08-16T15:40:20Z), Gap 9 — la seconda metà dello split del
container di controllo: ospita `aidr` (vendor, commit pinnato
`7fad14d2478707e68a09b8ecd9942dec8fde1614`) e il pacchetto `detector_adapter`
(`vendor_proxy.py`, Task 1); nessun `toy_agent` installato in questa
immagine. Scansionata il 2026-08-16 con lo stesso comando dockerizzato
(Trivy non installato come binario sulla macchina host):

    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ \
      aquasec/trivy image --severity CRITICAL --exit-code 1 agentic-security-audits-detector

**4 vulnerabilità CRITICAL residue**, tutte sul pacchetto `perl-base`
(`CVE-2026-13221`, `CVE-2026-42496`, `CVE-2026-57433`, `CVE-2026-8376`) —
esattamente le stesse 4 CVE già documentate sopra per `control` e `agent`,
stessa causa radice: `perl-base` è parte del set essenziale Debian e resta
presente in qualunque immagine `python:3.11-slim`, indipendentemente dal
Dockerfile. Exit code: 1. Nessuna CVE CRITICAL aggiuntiva/diversa rispetto a
`control`/`agent`.

Questa immagine `detector` (`docker/detector/Dockerfile`) applica lo stesso
controllo compensativo già in atto per `control` e `agent` — `chmod a-x
/usr/bin/perl /usr/bin/perl5.40.1` come ultimo passo di build — e ricade
sotto la **stessa eccezione già accettata dal titolare del progetto
(2026-08-15)**: nessuna delle 4 CVE ha una fix disponibile a questa data, e
nessun codice di questa immagine (`entrypoint.sh`, `detector_adapter`,
`aidr`) invoca mai perl su alcun percorso — questa immagine conserva lo
stage di build separato con `git` (necessario qui per clonare il repo
vendor pinnato, a differenza di `agent`), ma quello stage resta uno stage
di build separato (`vendor-source`), scartato prima dell'immagine finale,
per la stessa ragione già documentata per `control`. Non è una nuova
decisione di rischio da discutere: è la stessa eccezione, riapplicata a una
terza immagine che condivide la stessa causa non risolvibile lato Debian.

## Controlli compensativi in atto

1. **Riduzione della superficie (multi-stage build, Task 4)**: `git` — e
   quindi i pacchetti `perl`, `libperl5.40`, `perl-modules-5.40` che
   `git` porta come dipendenza Debian — è installato ed eseguito solo in
   uno stage di build separato (`vendor-source` in
   `docker/control/Dockerfile`), usato unicamente per clonare il repo
   vendor pinnato. Lo stage finale non installa `git` né questi 3 pacchetti.
   Questo ha portato le CVE CRITICAL da 16 a 4 (`perl-base`, che è
   parte del set essenziale Debian e resta presente in qualunque immagine
   `python:3.11-slim`, indipendentemente da questo Dockerfile, non è
   rimovibile con questa tecnica).

2. **Bit di esecuzione rimosso dall'interprete Perl (defense-in-depth,
   Task 4)**: come ultimo passo di build prima di `ENTRYPOINT`, il
   Dockerfile esegue `chmod a-x /usr/bin/perl /usr/bin/perl5.40.1` (i due
   binari reali che `perl-base` installa — hardlink allo stesso inode,
   entrambi resi non eseguibili esplicitamente). Verificato dopo il build:

       $ docker run --rm --entrypoint bash <control-image> -c "ls -la /usr/bin/perl /usr/bin/perl5.40.1"
       -rw-r--r-- 1 root root 3931280 Jul 27  2025 /usr/bin/perl
       -rw-r--r-- 1 root root 3931280 Jul 27  2025 /usr/bin/perl5.40.1

       $ docker run --rm --entrypoint bash <control-image> -c "perl -e 'print 1'"
       bash: line 1: /usr/bin/perl: Permission denied   (exit 126)

   Questo non cambia il conteggio di Trivy (che scansiona i metadati dpkg,
   non i permessi dei file) — le 4 CRITICAL restano riportate, come atteso e
   documentato qui. Riduce la superficie di attacco per invocazione
   accidentale o non privilegiata; non è una difesa contro un attaccante che
   ottenga già esecuzione di codice come root nel container (che potrebbe
   ripristinare il bit di esecuzione con `chmod +x`, o invocare l'interprete
   direttamente tramite `ld-linux.so`, dato che il file resta leggibile da
   tutti). Verificato che nessuno step di build residuo o `entrypoint.sh` dipenda da
   perl eseguibile: il container è stato ricostruito e avviato con successo
   dopo questa modifica (vedi report Task 4 per il log completo del test di
   fumo — il container resta in stato `running` con il flusso di
   readiness delle porte 8100/8101/8102 di `entrypoint.sh` invariato).

3. **Egress di rete bloccato (Task 3)**: `control` non ha alcuna rotta di
   rete in uscita se non verso `openrouter.ai`, tramite il sidecar
   `egress-proxy` (Squid), su una rete Docker `internal: true`. Anche nel
   caso peggiore — una RCE via Perl sfruttando una di queste CVE — l'unica
   destinazione di rete raggiungibile dall'interno di `control` è
   `openrouter.ai`: non un canale generico di exfiltrazione o
   comando-e-controllo, ma comunque una destinazione reale, raggiungibile,
   con una chiave API valida presente nell'ambiente — non una superficie
   nulla.

## Note

Scansione iniziale (Dockerfile a singolo stage, prima di questo task):
`control` riportava 16 CRITICAL — le stesse 4 CVE elencate sopra, ciascuna
replicata su 4 pacchetti Debian (`libperl5.40`, `perl`, `perl-base`,
`perl-modules-5.40`). Nessuna delle 4 CVE aveva (e ha tuttora) una "Fixed
Version" in Trivy — confermato indipendentemente controllando
`apt-cache policy perl-base` dentro `python:3.11-slim`: `Installed` e
`Candidate` sono identici (5.40.1-6), nessun aggiornamento disponibile nei
repository Debian trixie a questa data. `python:3.11-slim` risultava già
essere il digest più recente disponibile (`docker pull` non ha scaricato
nulla di nuovo).

Indagine su una possibile risoluzione completa: 3 dei 4 pacchetti coinvolti
(`perl`, `libperl5.40`, `perl-modules-5.40`) risultavano installati solo come
dipendenza di `git` (necessario solo in fase di build, per clonare il repo
vendor pinnato — mai a runtime). Il quarto pacchetto, `perl-base`, è parte
del set minimale/essenziale di Debian e viene installato comunque
nell'immagine base `python:3.11-slim`, indipendentemente da qualunque cosa
faccia questo Dockerfile — non esiste quindi una modifica al Dockerfile che
porti lo scan a 0 CRITICAL oggi (2026-08-15), perché Debian non ha ancora
pubblicato una patch per `perl-base` per queste 4 CVE.

Percorso seguito: multi-stage build per isolare `git`/`perl`/`libperl5.40`/
`perl-modules-5.40` in uno stage di sola build (16 → 4 CVE), seguito da
`chmod a-x` sui binari perl residui come controllo compensativo (non cambia
il conteggio Trivy, chiude il percorso di sfruttamento). Le 4 CRITICAL
residue su `perl-base` sono state discusse esplicitamente con l'utente
(2026-08-15) e accettate come rischio documentato — non silenziosamente
soppresse con `--ignore-unfixed` — sulla base delle mitigazioni elencate
sopra (superficie ridotta, interprete non eseguibile, egress di rete
bloccato) e del fatto che nessun percorso di questo progetto invoca perl.
Se Debian pubblica una fix per `perl-base`, questo file va aggiornato e lo
scan ripetuto per verificare 0 CRITICAL su entrambe le immagini.
