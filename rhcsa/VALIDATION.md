> Historisch document van de uitgangsversie. Zie [VALIDATION-CORRECTIONS.md](VALIDATION-CORRECTIONS.md) voor deze revisie.

# Validatie van deze oplevering

Uitgangspunt: de door de gebruiker aangewezen originele `rhcsa.zip`.
Alle oorspronkelijke inhoudelijke bestanden zijn overgenomen. Git-administratie,
IDE-metadata, macOS-resourceforks en de ingesloten `~`-map zijn niet opgenomen
in het distributiearchief.

Uitgevoerde controles op deze Mac:

- `bash -n` op het volledige vervangende `scripts/build-local-lab.sh`.
- Python-syntaxcontrole van `scripts/fusion-local-lab.py`.
- Kickstart-validatie met `ksvalidator -v RHEL10` voor servera en serverb.
- Tien gerichte tests: selectie van de hoogste geschikte ISO (met afwijzing van
  x86/bootmedia), aanpassing van echte vendor-GRUB-configuratie, disk- en
  netwerkconfiguratie, behoud van Fusion-instellingen bij VMX-wijzigingen,
  weigering bestaande VM-disks te overschrijven en veilig hervatten zonder
  de installer opnieuw te starten. Verder: hervatten met alleen een statusbestand,
  behoud van complete disks, niet publiceren van afgebroken diskcreatie en
  weigeren te hervatten bij een tegenstrijdige VMX.
- Werkelijke remaster van de aanwezige `Rocky-10.2-aarch64-dvd1.iso` met native
  xorriso 1.5.6.pl02 en mtools 4.0.49, tijdelijk gebouwd in de werkmap.
  Geen installatie van deze tools buiten de werkmap en geen Podman gebruikt.
- Controle van Rocky/aarch64-metadata, beide DVD-repositories en ARM EFI-loader.
- Teruglezen en vergelijken van GRUB uit de gewijzigde FAT EFI-image.
- Teruglezen en vergelijken van Kickstart, GRUB en EFI-image uit de nieuwe DVD.
- UEFI El Torito-bootcatalogus gecontroleerd; ook de werkelijke bootsectoren
  op de opgegeven LBA vergeleken met de gewijzigde EFI-image.
- Werkelijke proefdisks aangemaakt met Fusion's `vmware-vdiskmanager`:
  30 GiB = 62.914.560 sectoren; 10 GiB = 20.971.520 sectoren.
- Commandoregel-help en afhandeling van een ontbrekende optiewaarde gecontroleerd.
- Archiefintegriteit en ongewijzigde inhoud van alle overige repositorybestanden
  gecontroleerd.

**Niet uitgevoerd:** het starten en volledig installeren van de twee VM's.
De oplevering is dus geen claim van een geslaagde end-to-end gastinstallatie.
De gereedheidscontroles vinden tijdens de eerste echte uitvoering plaats;
het script meldt pas succes nadat beide geïnstalleerde gasten die doorstaan.
De tijdelijke test-ISO, proefdisks en tool-builds zijn geen onderdeel van de ZIP.

Laatste wijziging: Fusion-bundels onder `$HOME/Virtual Machines.localized`.
De nieuwe diskvoorbereiding is ook met de echte Fusion-disktool getest voor
30 en 10 GiB. Een tweede uitvoering behield alle descriptoren en extents
byte-voor-byte. Het startscript is vanuit `/private/tmp` aangeroepen met `--help`;
de helper werd correct gevonden. De tests wijzigden geen bestaande gebruikers-VM's.

## Wizard 2026-09-27-wizard-1

In de actuele nieuwe Rocky-VM is bevestigd dat Kickstart werd geladen en in
het pre-installatiescript stopte. De 30 GiB-disk is zichtbaar; de eerdere
screenshot met de grafische RHEL-installer hoorde bij de oude VM-locatie.
De exacte falende oude shelltest is niet meer vastgesteld nadat de VM werd
gepauzeerd. De afhankelijkheid van geformatteerde lsblk-uitvoer is vervangen
door expliciete sysfs-controles met foutmeldingen.

Twaalf tests slagen, inclusief geldige/ongeldige diskconfiguraties, invullen
van account/taal/tijdzone, wachtwoordhash in plaats van klare tekst en de
bestaande hervattingscontroles. De gerenderde wizard-Kickstart is met de
RHEL10-validator gecontroleerd. De volledige installatie met deze wijziging
is nog niet end-to-end bevestigd.

## Wizard-2: serverb en gastcontrole

Twee aanvullende tests controleren dat serverb ook na een controlefout bij
servera wordt verwerkt en dat de gastcontrole via een overgedragen shellbestand
wordt uitgevoerd. De gegenereerde shellsyntax is gecontroleerd. Live verificatie
in de geïnstalleerde gasten is nog niet uitgevoerd.
