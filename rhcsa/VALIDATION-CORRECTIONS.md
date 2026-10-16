# Validatie van de gecorrigeerde cursus

Datum: 2 oktober 2026.

Uitgevoerd met `python3 tools/validate_course.py`:

- Python-bronnen geparseerd en JSON geladen: twaalf weken.
- Vijf shell-entrypoints, 176 commandoblokken en zeven ingebedde scripts slagen voor Bash-syntaxcontrole.
- Alle twaalf gegenereerde labpagina's komen overeen met de bronsecties en break/fix-opdrachten.
- De volledige scripts in vier cloudpagina's komen overeen met de cloudbuilder.
- Argumentverwerking getest met ontbrekende en ongeldige argumenten, spaties, nul, voorloopnullen en grenswaarden.
- Partitiebenaming getest voor SATA, NVMe en MMC.
- Vier cloudlifecycles getest met lokale nagebootste CLI-antwoorden: aanmaken, herhaald aanmaken weigeren, verwijderen zonder openbare sleutel, status archiveren en status behouden na een gesimuleerde fout.

Deze controles voeren geen Linux-beheeropdrachten op een echte gast uit. Er is geen nieuwe VM geïnstalleerd, geen hypervisor bediend en geen live cloud-API aangeroepen. Syntax- en mocktests bewijzen niet dat elk pakket, provider-image, CLI-versie of gastgedrag beschikbaar is. De instructies zijn bedoeld voor Rocky/RHEL 10; voer na installatie de aangegeven functionele controles binnen de gasten uit.

Cloud-integratie, providerrechten, API-vlaggen, resourcequota en actuele image-ID's vereisen nog een live controle. Gebruik voor aanmaken en verwijderen hetzelfde provideraccount/project. Bewaar de lokale status; controleer na verwijderen ook de providerconsole op achtergebleven of factureerbare resources. Vultr gebruikt een vooraf geconfigureerde firewallgroep die bewust behouden blijft. Bij gedeeltelijk mislukte provisioning kunnen handmatige herstelstappen nodig zijn.

`VALIDATION.md` is het historische validatiedocument van de uitgangsversie; bovenstaande resultaten beschrijven deze revisie. Herhaal de controle na een wijziging. Na aanpassen van labbronnen: genereer eerst de pagina's met `python3 tools/build_labs.py` en controleer daarna opnieuw.

Primaire bron voor doctl-regelnotatie (meerdere regels gescheiden door spaties): https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/create/
