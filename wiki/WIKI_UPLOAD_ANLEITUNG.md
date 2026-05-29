# Wiki zu GitHub hochladen

GitHub-Wikis sind technisch eigene Git-Repositories.

## Variante 1: Per GitHub-Weboberfläche

1. Repository auf GitHub öffnen.
2. Tab **Wiki** öffnen.
3. Erste Seite erstellen.
4. Inhalte aus den Markdown-Dateien hier einzeln einfügen.
5. Dateinamen als Seitentitel verwenden.

## Variante 2: Wiki per Git klonen

Wenn das Repository z. B. heißt:

```text
https://github.com/<user>/<repo>
```

dann ist das Wiki-Repository:

```bash
git clone https://github.com/<user>/<repo>.wiki.git
```

Dann die Markdown-Dateien aus dem Ordner `wiki/` in das Wiki-Repository kopieren:

```bash
cp wiki/*.md <repo>.wiki/
cd <repo>.wiki
git add .
git commit -m "Add project wiki"
git push
```

Danach sind die Seiten im GitHub-Wiki sichtbar.
