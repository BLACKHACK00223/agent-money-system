"""
ATTENTION: Ce fichier utilise Win32Raw (python-escpos) qui est WINDOWS-UNIQUEMENT.
Il ne peut PAS fonctionner sur Railway (Linux). Gardé pour usage local.
Pour l'impression sur Railway, utiliser l'API Web Bluetooth (bluetooth-print.js).
"""
from flask import Flask, request, jsonify
import requests
from escpos.printer import Win32Raw

app = Flask(__name__)

PRINTER = "XP-58-BLACK"

@app.route("/print")
def print_ticket():
    url = request.args.get("url")

    try:
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

        return jsonify({"status": "printed"})

    except Exception as e:
        return jsonify({"error": str(e)})

app.run(port=5000)