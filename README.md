# athena-model

Modello economico in Python (solo libreria standard) per un **assemblatore di server Arm senza GPU**
basati su SiPearl Athena1, con tre linee di prodotto da 16, 32 e 64 core, venduti a un distributore.

> Tutti i valori in `config/default.json` sono **ipotesi** da sostituire con preventivi reali.
> Il prezzo di Athena1 non è pubblico. Il modello serve a ragionare sugli ordini di grandezza e non è
> una consulenza finanziaria.

## Cosa calcola
- **Unit economics** per linea: distinta base (chip, RAM, scheda/chassis/rete/NVMe), prezzo al distributore,
  margine lordo, riserva garanzia, margine netto, margine annuo del supporto.
- **Scenari di volume** (prudente, base, ottimistico): ricavi, costo dei componenti, margine, supporto ricorrente.
- **Costi di avvio** (progettazione, firmware e stack, certificazioni, legale): minimo, centrale, massimo.
- **Capitale circolante** (intervallo in giorni di ciclo) e **tempo di rientro**.
- **Flusso di cassa annuale** dal 2027, con supporto sul parco installato.
- **Sensibilità** su prezzo del chip e della RAM, con o senza adeguamento del prezzo di vendita.

## Uso
```bash
python -m athena_model                              # tutti gli scenari
python -m athena_model --scenario base --sensitivity
python -m athena_model --config config/default.json --export out/   # CSV
pip install -r requirements-dev.txt && pytest       # test
```
Serve Python 3.10 o superiore.

## Struttura
```
athena_model/config.py   dati e validazione
athena_model/model.py    calcoli
athena_model/cli.py      riga di comando ed esportazione CSV
config/default.json      ipotesi (modificabili)
tests/test_model.py      test
```

## Ipotesi principali (da verificare)
- RAM a 7 €/GB, volatile; margine lordo circa 24% sul prezzo al distributore.
- Riserva garanzia 2,5% del prezzo; supporto di terzo livello 6% annuo del prezzo, margine 30%.
- Prime vendite nel 2028; Athena1 è indicata per la seconda metà del 2027 o per il 2028 a seconda delle fonti.
- Athena1 non ha HBM: la banda di memoria è quella della DDR5, quindi il prodotto è adatto a edge,
  ambienti isolati e carichi con pochi utenti, non all'inferenza ad alta concorrenza.

## Pubblicare su GitHub
```bash
git init -b main
git add .
git commit -m "Modello economico Athena1"
gh repo create athena-model --private --source=. --push
```
