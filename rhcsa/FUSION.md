## Aanvulling bij de revisie van 2 oktober 2026

Lees [scripts/README.md](scripts/README.md). Onbemande installatie met `--yes` vereist `RHCSA_PASSWORD`. De installatietemplate bevat nu de extra pakketten voor de labs en start crond en rsyslog. Vervang `shea` in opdrachten als je een ander account hebt gekozen.

Een geblokkeerde rd.break-console kan voorkomen terwijl root in het geïnstalleerde systeem een geldig wachtwoord heeft. Gebruik de bijgewerkte week-5-herstelroute. Bij `init=/bin/bash` is de geïnstalleerde root al `/`: remount `/`, niet `/sysroot`.

De gereedheidscontrole hoort bij de eerste installatie en verwacht ongepartitioneerde oefendisks. Nadat opslaglabs zijn uitgevoerd, start je bestaande VM's rechtstreeks vanuit Fusion; partitionering is dan normaal.

# RHCSA automatisch installeren

## Eén startpunt

Dubbelklik op **Start-RHCSA.command** in deze repository. Het terminalvenster
vermeldt versie `2026-09-27-wizard-2` en het exacte scriptpad. Er is geen andere
ZIP of alternatieve repository nodig.

De wizard vraagt bij een nieuwe installatie:

1. Beheeraccount (standaard `shea`).
2. Wachtwoord, tweemaal en zonder het op het scherm te tonen.
3. Systeemtaal: `en` of `nl`.
4. Tijdzone (standaard `UTC`, bijvoorbeeld `Europe/Amsterdam`).
5. Startbevestiging.

Daarna maakt het script de installatie-DVD's, disks en VM's, installeert Rocky,
start vanaf de systeemdisk en controleert het resultaat. Je hoeft geen vragen
in de Linux-installer te beantwoorden.

## Automatisch gekozen instellingen

- Rocky Linux 10.x aarch64 DVD uit `$HOME/Downloads/Images`.
- VM's: `$HOME/Virtual Machines.localized/servera.vmwarevm` en `serverb.vmwarevm`.
- Zichtbare Fusion-namen: **servera — Rocky RHCSA** en **serverb — Rocky RHCSA**.
- Beide: 2 CPU, 4 GB geheugen, 30 GiB NVMe-systeemdisk, UEFI, NAT en host-only.
- Servera: extra lege 10 GiB labdisk, pas aangesloten na de installatie.
- Host-only-adressen: 192.168.56.10 en 192.168.56.11.
- SSH en firewalld actief, SELinux enforcing, beheeraccount in wheel.
- De Mac gebruikt de NAT-adressen die het script na installatie toont.

De systeemdiskcontrole gebruikt kernelinformatie uit sysfs en stopt met een
expliciete melding bij een ontbrekende, verkeerde of extra disk. De labdisk
is tijdens de installatie niet aangesloten. Kickstart partitioneert alleen
`nvme0n1`; de systeemdisk moet exact 30 GiB zijn.

## Eerdere poging aanwezig

Je krijgt eerst de keuze **hervatten** of **bewaren en nieuw installeren**.
Bij nieuw installeren worden bestaande beheerde bundels volledig verplaatst
naar een aparte `RHCSA-backup-...`-map in de Fusion-map. Ze worden niet verwijderd.
Sluit een draaiende VM eerst volledig af; een actieve of vergrendelde VM wordt
niet geforceerd gestopt of verplaatst. Een gepauzeerde VM met lock moet eerst
volledig afgesloten worden.

Voor een poging die met de vorige Kickstart op de diskcontrole vastliep, kies
**nieuw installeren** nadat die VM volledig is afgesloten. Hervatten van die
oude poging voert nog steeds de oude installatie-ISO uit.

Bij hervatten blijven gebruikersnaam, taal en tijdzone behouden. De wizard
vraagt het bestaande wachtwoord voor de controles; de oude versie gebruikte
`shea` / `rhcsa`. Hervatten verandert geen bestaand wachtwoord.

Oude RHEL-VM's in `$HOME/rhcsa-labs/vmware` horen niet bij deze workflow. Ze worden
niet verplaatst of verwijderd. Open voor deze installatie de vensters met
**Rocky RHCSA** in de titel.

## Benodigdheden

VMware Fusion op Apple Silicon, Python 3, xorriso, mtools en OpenSSL 3.
Ontbrekende hulpmiddelen zijn via Homebrew beschikbaar:

```bash
brew install python xorriso mtools openssl@3
```

Gebruik je gewone Mac-account, zonder sudo. Houd circa 40 GB vrije ruimte
beschikbaar, plus ruimte voor eventuele bewaarde eerdere VM's.
Er worden geen Podman-containers of Linux loop devices gebruikt.

Het wachtwoord wordt alleen tijdens deze uitvoering in het geheugen gebruikt;
Kickstart en het voortgangsbestand bevatten een gezouten SHA-512-hash. Fusion's
vmrun ontvangt het wachtwoord voor de gastcontroles via zijn commandoregel.
Een latere uitvoering vraagt het wachtwoord opnieuw.

## Terminalalternatief

Het werkende pad is onafhankelijk van je huidige map:

```bash
"$HOME/Studies/RHCSA/labs/learnlinuxforwork/rhcsa/scripts/build-local-lab.sh" --provider vmware
```

`--prepare-only` maakt alleen bestanden. `--timeout 120` geeft per VM twee uur.
`--version` toont de versie. `--yes` slaat vragen over voor geautomatiseerd
gebruik; stel dan `RHCSA_PASSWORD` in. Zonder die variabele gebruikt `--yes`
het oude oefenwachtwoord `rhcsa` en de bestaande cursusdefaults.

Bij fouten blijven VM's behouden. Lees de terminalmelding en eventueel
`preparation-error.txt` in de VM-bundel. Het voortgangsbestand is
`fusion-state.json`; fouten vóór partitionering staan in `/tmp/rhcsa-pre.log`
in de installer. Zie `VALIDATION.md` voor de uitgevoerde controles.

Beide VM-bundels worden nu voorbereid voordat de installatiecontroles beginnen.
Een fout bij servera verhindert de verwerking van serverb niet. De gastcontrole
wordt als bestand overgedragen; resultaten staan in `guest-check.log` in de
VM-bundel. Een controlepoging heeft een limiet van circa vijf minuten.
