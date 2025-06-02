# sqlmap ![](https://i.imgur.com/fe85aVR.png)

[![.github/workflows/tests.yml](https://github.com/sqlmapproject/sqlmap/actions/workflows/tests.yml/badge.svg)](https://github.com/sqlmapproject/sqlmap/actions/workflows/tests.yml) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/license-GPLv2-red.svg)](https://raw.githubusercontent.com/sqlmapproject/sqlmap/master/LICENSE) [![Twitter](https://img.shields.io/badge/twitter-@sqlmap-blue.svg)](https://twitter.com/sqlmap)

Το sqlmap είναι πρόγραμμα ανοιχτού κώδικα, που αυτοματοποιεί την εύρεση και εκμετάλλευση ευπαθειών τύπου SQL Injection σε βάσεις δεδομένων. Έρχεται με μια δυνατή μηχανή αναγνώρισης ευπαθειών, πολλά εξειδικευμένα χαρακτηριστικά για τον απόλυτο penetration tester όπως και με ένα μεγάλο εύρος επιλογών αρχίζοντας από την αναγνώριση της βάσης δεδομένων, κατέβασμα δεδομένων της βάσης, μέχρι και πρόσβαση στο βαθύτερο σύστημα αρχείων και εκτέλεση εντολών στο απευθείας στο λειτουργικό μέσω εκτός ζώνης συνδέσεων.

Εικόνες
----

![Screenshot](https://raw.github.com/wiki/sqlmapproject/sqlmap/images/sqlmap_screenshot.png)

Μπορείτε να επισκεφτείτε τη [συλλογή από εικόνες](https://github.com/sqlmapproject/sqlmap/wiki/Screenshots) που επιδεικνύουν κάποια από τα χαρακτηριστικά.

Εγκατάσταση
----

Έχετε τη δυνατότητα να κατεβάσετε την τελευταία tarball πατώντας [εδώ](https://github.com/sqlmapproject/sqlmap/tarball/master) ή την τελευταία zipball πατώντας [εδώ](https://github.com/sqlmapproject/sqlmap/zipball/master).

Κατά προτίμηση, μπορείτε να κατεβάσετε το sqlmap κάνοντας κλώνο το [Git](https://github.com/sqlmapproject/sqlmap) αποθετήριο:

    git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git sqlmap-dev

Το sqlmap λειτουργεί χωρίς περαιτέρω κόπο με την [Python](https://www.python.org/download/) έκδοσης **3.11+** σε
