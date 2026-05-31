import requests
import sys
from escpos.printer import Win32Raw

PRINTER = "XP-58-BLACK"

def print_ticket(url):
    data = requests.get(url).json()

    p = Win32Raw(PRINTER)

    line = "-" * 32

    p.set(align='center')
    p.text(data["service"] + "\n")
    p.text(data["adresse"] + "\n")
    p.text("TEL: " + data["telephone"] + "\n")
    p.text(line + "\n")

    p.text(data["role"].upper() + ": " + data["user"] + "\n")
    p.text(line + "\n")

    p.text("TYPE: " + data["type"].upper() + "\n")
    p.text(line + "\n")

    p.set(align='left')
    p.text("OPERATEUR: " + data["operateur"] + "\n")
    p.text("CLIENT: " + data["client"] + "\n")

    if data["nom_client"]:
        p.text("NOM: " + data["nom_client"] + "\n")

    p.text(line + "\n")

    p.set(align='center', width=2, height=2)
    p.text(str(data["montant"]) + " FCFA\n")

    p.cut()


if __name__ == "__main__":
    url = sys.argv[1]
    print_ticket(url)