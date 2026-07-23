# 11888 Scraper

Python scraper για σελίδες του ελληνικού τηλεφωνικού καταλόγου 11888. Ανοίγει
τις σελίδες με headless Google Chrome και αποθηκεύει τις επαφές σε τοπική βάση
SQLite.

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

Η βάση και το `contacts.csv` δημιουργούνται στον φάκελο από τον οποίο τρέχεις
τις εντολές. Για αυτό όλες οι παρακάτω εντολές εκτελούνται μέσα στον φάκελο του
repository.

## Απαιτήσεις

- Python 3
- Google Chrome εγκατεστημένο
- Git, μόνο αν θα κάνεις clone το repository
- Σύνδεση στο Internet

Στο macOS το script ελέγχει το Chrome στην προεπιλεγμένη διαδρομή:

```text
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
```

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

Κάθε φορά που ανοίγεις καινούριο Terminal:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
source .venv/bin/activate
python autoscrap.py
```

Εναλλακτικά, χωρίς ενεργοποίηση του virtual environment:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
.venv/bin/python autoscrap.py
```

Η επιτυχής εκκίνηση εμφανίζει μηνύματα όπως:

```text
[*] Booting session. Proxy: Direct IP
Scraping page 123: https://www.11888.gr/white-pages/123/
Inserted: ...
```

- `Inserted:` σημαίνει ότι αποθηκεύτηκε νέα επαφή.
- `No contact on page ...` σημαίνει ότι η συγκεκριμένη σελίδα δεν είχε
  αναγνωρίσιμη επαφή. Δεν είναι σφάλμα.
- Κάθε επαφή γίνεται `commit` αμέσως στη βάση.
- Αν υπάρχει ήδη βάση, το script συνεχίζει από το μεγαλύτερο αποθηκευμένο
  `page` συν ένα.

### Διακοπή

Για να σταματήσεις το scraper πάτησε:

```text
Control + C
```

Οι εγγραφές που είχαν ήδη εμφανίσει `Inserted:` παραμένουν αποθηκευμένες.

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

### `ModuleNotFoundError: No module named 'undetected_chromedriver'`

Δεν έχουν εγκατασταθεί οι εξαρτήσεις στο Python environment που χρησιμοποιείς:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
source .venv/bin/activate
python -m pip install -r requirements.txt
python autoscrap.py
```

### Δεν ανοίγει το Chrome

Επιβεβαίωσε ότι είναι εγκατεστημένο:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version
```

Έπειτα ενημέρωσε το Chrome και ξανατρέξε:

```bash
cd /Users/mersin/Desktop/18888/11888-scrapper
.venv/bin/python autoscrap.py
```

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
sqliteToCSV.py     εξαγωγή της βάσης σε contacts.csv
requirements.txt  Python dependencies
11888_data.db      SQLite βάση αποτελεσμάτων
```
