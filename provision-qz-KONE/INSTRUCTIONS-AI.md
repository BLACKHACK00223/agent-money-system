# GUIDE D'INSTALLATION COMPLET — QZ Tray pour le site KONE
## À l'intention de l'IA / technicien travaillant sur CE PC (le PC d'impression)

> Contexte : ce PC doit imprimer des tickets (imprimante thermique **USB**) depuis le site
> web `kone-service.saheltech.tech` en passant par **QZ Tray** (logiciel local).
> L'objectif : que l'impression fonctionne SANS aucune popup d'autorisation.

---

## ÉTAPE 0 — Vérifier ce que contient ce dossier `provision-qz`

| Fichier | Rôle |
|---|---|
| `digital-certificate.txt` | Le certificat (clé publique) du site KONE — à installer dans QZ Tray |
| `installer.bat` | Script d'installation automatique (overwrite `override.crt` + redémarrage) |
| `provision.json` | Méthode de secours n°2 (provisioning QZ) |
| `verifier.ps1` | Script de vérification de l'installation |
| `INSTRUCTIONS-AI.md` | Ce guide |

---

## ÉTAPE 1 — QZ Tray est-il installé ? Quelle version ?

1. Cherchez QZ Tray : menu Démarrer → « QZ Tray ».
   - S'il n'existe pas : téléchargez-le sur **https://qz.io/download/** (version Windows 2.x)
     et installez-le (installation par défaut, tout cocher par défaut).
   - S'il existe : vérifiez la **version**. Clique droit sur l'icône QZ Tray (barre des
     tâches, près de l'horloge) → **About**.
   - **IMPORTANT : il faut la version 2.1 ou plus** (le fichier `override.crt` n'existe
     qu'à partir de 2.1). Si la version est inférieure, mettez à jour QZ Tray depuis
     https://qz.io/download/ (l'installeur met à jour l'installation existante).

Commandes PowerShell pour vérifier :

```powershell
# Dossier d'installation
Test-Path "C:\Program Files\QZ Tray\qz-tray.exe"
Test-Path "C:\Program Files (x86)\QZ Tray\qz-tray.exe"

# Version
(Get-Item "C:\Program Files\QZ Tray\qz-tray.exe").VersionInfo.FileVersion
```

---

## ÉTAPE 2 — Installer le certificat KONE dans QZ Tray (le point crucial)

**Méthode principale (recommandée) : `override.crt`**

QZ Tray lit automatiquement un fichier `override.crt` dans son dossier d'installation ;
s'il existe, le certificat qu'il contient remplace le certificat racine de confiance QZ.
Le site se signant avec la clé privée correspondante sera alors **approuvé automatiquement,
sans aucune popup**. C'est la méthode documentée officiellement
(https://qz.io/docs/signing → « To override the Trusted Root certificate »).

Deux possibilités :

**Option A — script automatique (recommandé) :**
1. Clic droit sur `installer.bat` → **Exécuter en tant qu'administrateur**
2. Le script copie `digital-certificate.txt` dans le dossier QZ Tray sous le nom
   `override.crt` et redémarre QZ Tray.

**Option B — manuelle :**
```powershell
# Trouver le dossier (normalement C:\Program Files\QZ Tray ou (x86))
Copy-Item "C:\Users\PUBLIC\Desktop\provision-qz\digital-certificate.txt" "C:\Program Files\QZ Tray\override.crt" -Force
# Puis quitter QZ Tray : icône dans la barre des tâches → Quit, et relancer
```

---

## ÉTAPE 3 — Vérifier l'installation

Lancez le script de vérification (clic droit → Exécuter avec PowerShell) :

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\PUBLIC\Desktop\provision-qz\verifier.ps1"
```

Il doit confirmer : QZ Tray présent ✅, version ≥ 2.1 ✅, `override.crt` présent et identique
au certificat du dossier ✅, QZ Tray en cours d'exécution ✅.

---

## ÉTAPE 4 — Tester l'impression réelle

1. Ouvrez Chrome ou Edge (dernière version) sur **https://kone-service.saheltech.tech**
2. Connectez-vous avec le compte du gérant (ID admin)
3. Allez dans une transaction (FORMULAIRE TRANSACTION) et cliquez **Imprimer**
4. Résultat attendu : l'imprimante USB imprime le ticket **sans aucune popup**.

---

## ÉTAPE 5 — Si une popup « Allow » apparaît quand même (CAS LIMITE)

1. Dans la popup QZ Tray, cochez **« Remember this decision »** puis cliquez **Allow**.
   → QZ la mémorise dans `%APPDATA%\qz\allowed.dat` et ne redemande plus.
2. Faites ensuite un test : imprimez une 2ᵉ fois → plus de popup.

---

## ÉTAPE 6 — Dépannage si l'impression ne fonctionne toujours pas

Vérifiez dans l'ordre :

1. **QZ Tray tourne-t-il ?** Icône jaune/bleue près de l'horloge. Sinon lancez-le.
2. **L'imprimante USB est-elle reconnue par Windows ?**
   Paramètres → Périphériques → Imprimantes : l'imprimante thermique doit être visible.
   Testez une impression de page de test Windows (clic droit sur l'imprimante → Imprimer une page de test).
   Sinon, installez le pilote du constructeur (ex. : théorie des fabricants Xprinter, etc.).
3. **Le site charge-t-il bien qz-tray.js ?**
   Dans Chrome : F12 → Console → onglet Réseau → rechargez la page → vérifiez que
   `qz-tray.js`, `digital-certificate.txt` et `sign-message` renvoient du 200 (sinon 403/404).
4. **Le sign-message fonctionne-t-il ?**
   Dans la console JS (F12) après un clic Imprimer : ne doit PAS y avoir d'erreur
   « Signature request rejected ».
5. **Le site est-il bien en HTTPS ?** QZ Tray refuse les sites HTTP non locaux.
6. **Méthode de secours n°2 — provisioning :**
   Copiez `provision.json` + `digital-certificate.txt` dans `C:\Program Files\QZ Tray\provision\`
   (créez le dossier s'il manque) puis quittez et relancez QZ Tray.
7. **Dernier recours :** notez précisément le message d'erreur exact (titre + texte complet
   de la popup, ou texte de l'erreur dans la console du navigateur + capture d'écran).

---

## RÉCAP — Ce qu'une installation réussie doit donner

```
C:\Program Files\QZ Tray\
├── qz-tray.exe
└── override.crt   ← notre certificat (digital-certificate.txt renommé)
```
QZ Tray visible dans la barre des tâches. Impression du ticket directe, sans popup.