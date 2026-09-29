# Gustav Klimt – Der Kuss

Die überarbeitete Fassung (Schema 1.1) verwendet 16 unterschiedliche Lead-Tonfolgen,
11 Rhythmen, 6 Begleitmuster und 5 Bassmuster. Im bisherigen Projektordner starten:

```bash
python main.py interact output_klimt_kuss/composition.json
```

Wenn noch die alte Sitzung läuft, zuerst `quit` eingeben. Dann im neuen Programm:

```text
ports
```

Mit `port NUMMER` den angezeigten Chordcat auswählen. Beispielsweise `port 2`,
falls er als zweiter Ausgang aufgeführt wird. Anschließend:

```text
show 0 2
play 0 2
play 3 0
diagnostics
set energy 0.2
rebuild
save mein_klimt
```

Zelle `(0,2)` enthält die Kussgeste und Hände; `(3,0)` zeigt die Blumenwiese.
Zeilen und Spalten werden ab 0 gezählt. [Das nummerierte Raster](grid_overlay.png)
hilft bei der Auswahl. Die gesamte Folge steht in [midi/overview.mid](midi/overview.mid).

## Ergebnis der überarbeiteten Interpretation

| Eigenschaft | Ergebnis |
| --- | --- |
| Tonart / Modus | D Ionian, entsprechend D-Dur |
| Tempo | 72 BPM |
| Dauer je Zelle | Zwei 4/4-Takte, ca. 6,67 Sekunden |
| Lead | Flöte |
| Begleitung | Orchesterharfe |
| Bass | String Ensemble 1 |
| Musikalische Epoche im Prototyp | Impressionist / Early Modern |
| Harmonie | I → V, jeweils mit diatonischer Septime und None |
| Globale normalisierte Entropie | 0,892471 |
| Mittlere HSL-Helligkeit | 0,445403 |
| Kantendichte | 0,240643 |
| Eingeschätzte globale Bewegung | 0,12 |
| Eingeschätzte Valenz | 0,57 |

Alle vier Interpretations-Offsets beginnen bei null. Das globale Tempo, die
Harmonie und die Instrumente sind unverändert. Lokale Merkmale werden jetzt
zusätzlich relativ zu allen 16 Zellen eingeordnet. Die Helligkeit beeinflusst
einen bevorzugten Melodiebereich; Entropie und Aktivität bestimmen vielfältigere
Rhythmen, Begleit- und Bassmuster. Eine gemeinsame Auswahl aus 20 gültigen
Lead-Kandidaten je Zelle berücksichtigt auch die visuellen Unterschiede zwischen
den Zellen. Es wird kein Zufall hinzugefügt.

Details stehen im [Vorher-nachher-Vergleich](DIVERSITY_COMPARISON.md).
Die ursprüngliche Version bleibt im Projektordner `output_klimt_kuss_v1/` erhalten.

## Bild und Einordnung

Verwendet wurde die 1280 × 1284 Pixel große digitale Reproduktion aus
[Wikimedia Commons / Google Art Project](https://commons.wikimedia.org/wiki/File:The_Kiss_-_Gustav_Klimt_-_Google_Cultural_Institute.jpg).
Die Originaldatei liegt unter `artworks/klimt_der_kuss/der_kuss.jpg` im Projekt.
Analysiert wurden alle Pixel dieser Version ohne weiteren Beschnitt oder
Größenänderung. Eine andere digitale Reproduktion oder Auflösung kann andere
Messwerte ergeben.

Das [Belvedere](https://sammlung.belvedere.at/objects/6678/der-kuss-liebespaar)
datiert das Werk auf etwa 1907–1909. Der Prototyp verwendet 1908 als einzelnes
Bezugsjahr innerhalb dieser Spanne, nicht als aus dem Bild erschlossenes Datum.
Alle Jahre dieser Spanne ergeben dieselbe musikalische Epoche im Prototyp.
Die Kunstbewegung ist als „Jugendstil / Wiener Secession“ gespeichert.

Die semantischen Werte wurden vom multimodalen Assistenten nach Sichtung des
Gesamtbildes und des 4×4-Rasters erstellt und als eigene Sidecar-Datei gespeichert.
Es erfolgte keine separate OpenAI-API-Anfrage. Die überwiegend positive Valenz,
geringe körperliche Bewegung und Objektkonfidenzen sind interpretative,
nicht kalibrierte Einschätzungen. Die quantitative Bildanalyse wurde dagegen
mit dem Programm berechnet.

Quellen und Vorgehen sind zusätzlich in
`artworks/klimt_der_kuss/provenance.json` dokumentiert. Die Sidecar-Datei heißt
`artworks/klimt_der_kuss/der_kuss.semantic.json`; sie kann für spätere identische
Analyseläufe wiederverwendet werden.

## Kontrolle

16 Zell-MIDIs mit jeweils drei Tracks sowie `overview.mid` wurden geprüft.
Ein erneuter Aufbau aus der gespeicherten Rohdatenanalyse erzeugt für alle
17 MIDI-Dateien identische Bytes. Prüfsummen stehen in `midi_sha256.json`.
Das MIDI-Gerät muss im lokalen Terminal ausgewählt werden; die abgeschirmte
Ausführungsumgebung des Assistenten erlaubt keine physische Wiedergabeprüfung.
