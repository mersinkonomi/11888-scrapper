# 11888 Scraper

Python scraper για σελίδες του ελληνικού τηλεφωνικού καταλόγου 11888.
Χρησιμοποιεί ελαφριά HTTP requests, τρέχει 10 παράλληλους workers και
αποθηκεύει όλες τις επαφές σε κοινή τοπική βάση SQLite.

> Χρησιμοποίησέ το μόνο όπου έχεις νόμιμο δικαίωμα συλλογής και επεξεργασίας
> των δεδομένων. Σεβάσου τους όρους χρήσης του ιστοτόπου, το απόρρητο και την
> ισχύουσα νομοθεσία.

## Τι αποθηκεύει

Τα αποτελέσματα γράφονται στο αρχείο `11888_data.db`, στον πίνακα `contacts`:

| Πεδίο | Περιγραφή |
| --- | --- |
| `id` | Αυτόματο αναγνωριστικό εγγραφής |
| `name` | Ονοματεπώνυμο |
| `location` | Περιοχή/τοποθεσία |
| `phones` | Τηλέφωνο ή τηλέφωνα |
| `page_url` | URL της σελίδας |
| `page` | Αριθμητικό ID σελίδας |

Η βάση δημιουργείται πάντα δίπλα στο `autoscrap.py`, ανεξάρτητα από τον φάκελο
από τον οποίο ξεκινάς την εντολή. Το `contacts.csv` δημιουργείται στον τρέχοντα
φάκελο όταν εκτελείς το `sqliteToCSV.py`.

## Απαιτήσεις

- Python 3
- Git, μόνο αν θα κάνεις clone το repository
- Σύνδεση στο Internet

## Εγκατάσταση από την αρχή

Άνοιξε το Terminal και εκτέλεσε ακριβώς:

```bash
git clone https://github.com/mersinkonomi/11888-scrapper.git
cd 11888-scrapper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Όταν το virtual environment είναι ενεργό, στην αρχή της γραμμής του Terminal
θα εμφανίζεται συνήθως `(.venv)`.

### Αν έχεις ήδη κατεβάσει το repository

Πήγαινε στον υπάρχοντα φάκελο και εγκατέστησε τις εξαρτήσεις:

```bash
cd /διαδρομή/προς/11888-scrapper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Για τη συγκεκριμένη τοπική διαδρομή:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Εκτέλεση

Για να ξεκινήσεις και τους 10 workers:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
./run_10_workers.sh
```

Ο launcher χρησιμοποιεί αυτόματα το `.venv` και χωρίζει το εύρος
`0–99.999.999` ως εξής:

```text
worker 0:  0–9.999.999
worker 1:  10.000.000–19.999.999
...
worker 9:  90.000.000–99.999.999
```

Η επιτυχής εκκίνηση εμφανίζει μηνύματα όπως:

```text
Starting worker 0: 0-9999999
[*] HTTP session. Proxy: Direct IP
Scraping page 90000009: https://www.11888.gr/white-pages/90000009/
Inserted: ...
```

- `Inserted:` σημαίνει ότι αποθηκεύτηκε νέα επαφή.
- `No contact on page ...` σημαίνει ότι η συγκεκριμένη σελίδα δεν είχε
  αναγνωρίσιμη επαφή. Δεν είναι σφάλμα.
- `HTTP 503 ... Retrying` σημαίνει προσωρινό σφάλμα του site. Ο worker
  περιμένει και δοκιμάζει ξανά την ίδια σελίδα χωρίς να τη χάσει.
- Κάθε επαφή γίνεται `commit` αμέσως στη βάση.
- Η πρόοδος κάθε range αποθηκεύεται στον πίνακα `scrape_progress`, ώστε η
  επόμενη εκτέλεση να συνεχίζει από εκεί που σταμάτησε.
- Δεν επιτρέπεται δεύτερο ταυτόχρονο batch από τον launcher.

Για έναν μόνο worker με δικό σου range:

```bash
.venv/bin/python autoscrap.py --start 90000000 --end 91000000
```

Τα logs κάθε batch δημιουργούνται σε νέο φάκελο, για παράδειγμα:

```text
logs/20260727_230500/worker_9.log
```

### Διακοπή

Για να σταματήσεις το scraper πάτησε:

```text
Control + C
```

Οι εγγραφές που είχαν ήδη εμφανίσει `Inserted:` παραμένουν αποθηκευμένες.
Ο launcher τερματίζει και τους 10 workers και αποθηκεύει την πρόοδό τους.

## Έλεγχος αποθηκευμένων εγγραφών

Στο macOS μπορείς να μετρήσεις τις εγγραφές με το προεγκατεστημένο `sqlite3`:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
sqlite3 11888_data.db "SELECT COUNT(*) FROM contacts;"
```

Για να δεις τις πέντε τελευταίες:

```bash
sqlite3 -header -column 11888_data.db \
  "SELECT id, name, location, phones, page FROM contacts ORDER BY id DESC LIMIT 5;"
```

Αν ένα γραφικό πρόγραμμα SQLite δείχνει παλιό αριθμό εγγραφών, πάτησε
**Refresh/Reload** ή κλείσε και ξανάνοιξε τη βάση. Βεβαιώσου ότι έχεις ανοίξει
το `11888_data.db` από τον ίδιο φάκελο στον οποίο εκτελείται το script.

## Εξαγωγή σε CSV

Με το virtual environment ενεργό:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
source .venv/bin/activate
python sqliteToCSV.py
```

Ή χωρίς ενεργοποίηση:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
.venv/bin/python sqliteToCSV.py
```

Θα δημιουργηθεί το αρχείο `contacts.csv`. Κάθε νέα εκτέλεση αντικαθιστά το
προηγούμενο CSV με νέο export της τρέχουσας βάσης.

Για να μετρήσεις τις γραμμές του CSV:

```bash
wc -l contacts.csv
```

Η πρώτη γραμμή είναι η επικεφαλίδα, επομένως ο αριθμός επαφών είναι μία λιγότερη
από το αποτέλεσμα του `wc -l`.

## Ενημέρωση υπάρχουσας εγκατάστασης

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
git pull
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Συνηθισμένα προβλήματα

### `ModuleNotFoundError: No module named 'requests'`

Δεν έχουν εγκατασταθεί οι εξαρτήσεις στο Python environment που χρησιμοποιείς:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
source .venv/bin/activate
python -m pip install -r requirements.txt
./run_10_workers.sh
```

### `Another 10-worker run is already active`

Υπάρχει ήδη ενεργό batch. Χρησιμοποίησε το υπάρχον Terminal ή σταμάτησέ το με
`Control + C` πριν ξεκινήσεις νέο.

### Το Terminal δείχνει συνεχώς `No contact`

Η σελίδα μπορεί να μην υπάρχει, να ανακατευθύνει στην αρχική σελίδα ή να έχει
αλλάξει η δομή του ιστοτόπου. Σε αυτή την περίπτωση δεν προστίθεται εγγραφή.

### Το CSV δείχνει λιγότερες εγγραφές από τη βάση

Το CSV είναι στιγμιότυπο της στιγμής που έγινε η εξαγωγή. Τρέξε ξανά:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
.venv/bin/python sqliteToCSV.py
```

## Αρχεία του project

```text
autoscrap.py       κύριο scraper
run_10_workers.sh  launcher για 10 παράλληλους workers
sqliteToCSV.py     εξαγωγή της βάσης σε contacts.csv
requirements.txt  Python dependencies
11888_data.db      SQLite βάση αποτελεσμάτων
logs/              ξεχωριστά logs ανά batch και worker
```
