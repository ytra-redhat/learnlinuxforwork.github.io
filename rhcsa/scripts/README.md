# Installatiescripts

## Lokale VM's

Voer de builder op de host uit. `build-local-lab.sh` ondersteunt x86_64 Linux met een bijpassende ISO en beschikbare VirtualBox/VMware-tools. Op macOS wordt de Fusion-builder gebruikt; zie `../FUSION.md` voor opties en ISO-keuze. Apple Silicon vereist een aarch64-ISO. Lees de hulpuitvoer vóór installatie.

De labs gebruiken `shea`, `servera`, `serverb` en een apart host-only-netwerk. Vervang het gebruikersaccount consequent als je bij installatie een andere naam kiest. Selecteer binnen de gast netwerkprofielen en oefendisks op basis van de getoonde gegevens. Gebruik geen systeemdisk als oefendisk.

Fusion met `--yes` vereist `RHCSA_PASSWORD`; er wordt geen standaardwachtwoord gekozen. Bewaar geen wachtwoord in een gedeeld script. VMware-gastcommando's kunnen wachtwoordargumenten tijdelijk zichtbaar maken in de proceslijst. De eerste installatie verwacht ongepartitioneerde extra disks. Start een bestaande lab-VM rechtstreeks in Fusion nadat je de opslaglabs hebt uitgevoerd.

`build-podman-lab.sh` levert slechts een gedeeltelijke omgeving. Bootherstel, echte disks, VM-netwerken en volledige SELinux-oefeningen vereisen VM's. De containeraccounts zijn uitsluitend voor een geïsoleerd oefenlab.

## Cloud

Cloudresources kosten geld. Installeer Python 3 en de officiële CLI, meld je aan bij het bedoelde account/project en controleer de prijzen en beschikbare images. Stel `RHCSA_SSH_CIDR` in op je eigen openbare IPv4-adres met `/32`. `RHCSA_SSH_KEY` kan het pad naar een openbare sleutel aanwijzen; standaard is dit `~/.ssh/id_ed25519.pub`.

DigitalOcean vereist `DO_KEY_ID`. Vultr vereist `VULTR_KEY_ID`, een geverifieerde Rocky 10 `VULTR_OS_ID` en `VULTR_FIREWALL_GROUP`. Deze firewallgroep moet SSH vanaf je eigen adres en benodigd verkeer tussen beide labhosts toelaten. Controleer dat het sleutel-ID hoort bij je lokale sleutel.

Gebruik `./scripts/build-cloud-lab.sh gcp` (of `aws`, `do`, `vultr`) voor aanmaken en dezelfde opdracht met `--destroy` voor verwijderen. Verwijderen gebruikt bijgehouden status onder `~/.local/state/rhcsa-cloud/<provider>`; `RHCSA_CLOUD_STATE` kan de bovenliggende statusmap wijzigen. Bewaar deze status en gebruik hetzelfde account/project. Een tweede create wordt geweigerd zolang eerdere status bestaat. Bij fouten blijft status beschikbaar voor herstel.

Cloudaccounts en adressen verschillen per provider; volg de verbindingsinformatie van het script en vervang accountnamen in de labs. De cloudomgeving is niet identiek aan het lokale tweekaartenlab. Zie `../VALIDATION-CORRECTIONS.md` voor de beperkingen van de tests.
