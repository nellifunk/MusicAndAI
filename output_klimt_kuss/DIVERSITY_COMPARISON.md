# Der Kuss: Vergleich vor und nach der Überarbeitung

Dieselbe Bilddatei, dieselben semantischen Einschätzungen, dieselben Rohdaten und
vier unveränderte Interpretations-Offsets von null. Kein erneuter Bild- oder
API-Analyselauf. Die Musik wurde mit der überarbeiteten Engine neu komponiert.

| Diagnose | Vorher, Schema 1.0 | Jetzt, Schema 1.2 |
| --- | ---: | ---: |
| Unterschiedliche Lead-Tonfolgen | 5 | 16 |
| Unterschiedliche Onset-Muster | 3 | 14 |
| Unterschiedliche Begleitmuster | 1 | 6 |
| Unterschiedliche Bassmuster | 1 | 5 |
| Redundante Lead-Tonfolgen | 11 | 0 |
| Größte Gruppe exakt doppelter Tonfolgen | 9 Zellen | Keine |
| Mittlere visuelle Paardistanz | 0,584254 | 0,584254 |
| Mittlere musikalische Paardistanz | 0,074891 | 0,145060 |
| Mittlere Paarstrafe für zu ähnliche Musik | 0,304517 | 0,236098 |

Tonfolgen werden anhand ihrer MIDI-Pitches verglichen, unabhängig vom Rhythmus.
„Redundant“ zählt weitere Zellen nach der ersten Verwendung derselben Tonfolge.
Begleit- und Bassmuster vergleichen Pitch, Einsatz und Dauer, ohne Lautstärke und Pan.
Die Distanzdefinition der neuen Engine wird in beiden Vergleichsspalten benutzt.

## Ehemalige exakte Wiederholungen

| MIDI-Tonfolge | Zellen (Zeile, Spalte) |
| --- | --- |
| 61, 62, 61, 59, 57 | (0,1), (0,2), (0,3), (1,2), (1,3), (3,0), (3,1), (3,2), (3,3) |
| 57, 61, 62, 61, 64 | (0,0), (2,0) |
| 64, 62, 61, 59, 57 | (1,0), (2,3) |
| 62, 61, 59, 57 | (1,1), (2,1) |

Die neue Fassung enthält keine exakt doppelte Lead-Tonfolge und verwendet ein
32-Schritt-Sechzehntelraster. Die vollständige,
maschinenlesbare Gegenüberstellung steht in `comparison.json`; die aktuelle
Diagnostik in `diagnostics.json`.

## Auswahlverfahren und musikalische Grenzen

Jede Zelle erhält 20 gültige Kandidaten aus einer deterministischen Beam-Suche
mit Breite 100. Nach Start bei den jeweiligen lokalen Optima verändert die
gemeinsame Auswahl die Kandidaten schrittweise in Zeilenreihenfolge. Nach vier
vollständigen Durchläufen ist die Belegung stabil. Die aktuelle Zielfunktion
endet bei 8,064935; die gesamte Verlaufskurve steht in `composition.json`.
Diese Optimierung ist näherungsweise und garantiert kein globales Minimum.

Alle drei Stimmen bleiben in ihren ursprünglichen Registern und in D Ionian.
Die gemeinsame Harmonie I → V mit Septimen und Nonen und 72 BPM sind unverändert.
Die neue Fassung spielt Lead als Flöte plus Violine, Begleitung als Harfe plus
Streicher und Bass als Cello. Bass und Begleitung verwenden nur
die Kerntöne des jeweiligen Akkords. Lead-Schrittgrenzen, mindestens drei
verschiedene Tonhöhen, keine dreifache Tonwiederholung, Taktgrenzen und die
Definition des Kadenzterms bleiben bestehen. Die sieben Gewichte wurden wie
angefordert geändert; es wurden keine harmonischen Regeln für Vielfalt entfernt.

Die automatisierten Prüfungen testen auch, dass die visuell verschiedensten
30 Zellpaare im Mittel musikalisch weiter auseinanderliegen als die visuell
ähnlichsten 30 Paare. Ähnliche Regionen werden nicht zwangsweise unterschieden;
16 einmalige Melodien sind ein Ergebnis dieses Bildes, keine erzwungene Quote.

Die ursprünglichen Dateien liegen in `../output_klimt_kuss_v1/`. Sie können
weiterhin unverändert abgespielt werden; ein `rebuild` einer alten Sitzung
erzeugt dagegen Musik mit der aktuellen Engine.
