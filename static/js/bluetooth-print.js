/**
 * KONE SERVICES - Impression Bluetooth ESC/POS
 * Utilise Web Bluetooth API (Android Chrome) avec fallback PDF + Web Share
 */

const KONEPrint = {
    connected: false,
    device: null,
    server: null,
    service: null,
    characteristic: null,

    // Configuration ESC/POS
    config: {
        encoding: 'CP437',
        width: 32,
        dotsPerLine: 576,
        density: 15,
    },

    // Vérifier si Web Bluetooth est supporté
    isSupported() {
        return navigator.bluetooth && /Android/i.test(navigator.userAgent);
    },

    // Vérifier si Web Share API est supporté
    canShare() {
        return navigator.share && /iPhone|iPad|iPod/i.test(navigator.userAgent);
    },

    // Scanner et connecter une imprimante Bluetooth
    async connect() {
        if (!this.isSupported()) {
            throw new Error('Web Bluetooth non supporté sur cet appareil');
        }

        const device = await navigator.bluetooth.requestDevice({
            acceptAllDevices: true,
            optionalServices: [
                '00001101-0000-1000-8000-00805f9b34fb', // Serial Port Profile (SPP)
                '000018f0-0000-1000-8000-00805f9b34fb', // Standard Printer
                '00001812-0000-1000-8000-00805f9b34fb', // Human Interface Device
            ]
        });

        this.device = device;

        device.addEventListener('gattserverdisconnected', () => {
            this.connected = false;
            this.device = null;
            this._onDisconnect();
        });

        this.server = await device.gatt.connect();
        this.connected = true;

        // Essayer de trouver le service SPP ou d'impression
        let service;
        try {
            service = await this.server.getPrimaryService('00001101-0000-1000-8000-00805f9b34fb');
        } catch (e) {
            try {
                service = await this.server.getPrimaryService('000018f0-0000-1000-8000-00805f9b34fb');
            } catch (e2) {
                // Chercher tous les services disponibles
                const services = await this.server.getPrimaryServices();
                for (const svc of services) {
                    const chars = await svc.getCharacteristics();
                    for (const ch of chars) {
                        if (ch.properties.write || ch.properties.writeWithoutResponse) {
                            service = svc;
                            this.characteristic = ch;
                            break;
                        }
                    }
                    if (this.characteristic) break;
                }
                if (!this.characteristic) {
                    throw new Error('Aucun service d\'impression trouvé');
                }
            }
        }

        if (service && !this.characteristic) {
            const characteristics = await service.getCharacteristics();
            for (const ch of characteristics) {
                if (ch.properties.write || ch.properties.writeWithoutResponse) {
                    this.characteristic = ch;
                    break;
                }
            }
        }

        if (!this.characteristic) {
            throw new Error('Aucune caractéristique d\'écriture trouvée');
        }

        this.service = service;
        localStorage.setItem('kone_bluetooth_printer', device.name || 'Bluetooth Printer');
        return device.name || 'Imprimante Bluetooth';
    },

    // Déconnecter
    disconnect() {
        if (this.device && this.device.gatt) {
            this.device.gatt.disconnect();
        }
        this.connected = false;
        this.device = null;
        this.server = null;
        this.service = null;
        this.characteristic = null;
        localStorage.removeItem('kone_bluetooth_printer');
    },

    // Callback de déconnexion
    _onDisconnect() {
        console.log('Imprimante Bluetooth déconnectée');
    },

    // Encoder le texte en CP437 pour ESC/POS
    _encodeText(text) {
        const encoder = new TextEncoder();
        const bytes = [];
        for (const char of text) {
            const code = char.charCodeAt(0);
            if (code < 128) {
                bytes.push(code);
            } else {
                // Mapping accents simples pour CP437
                const map = {
                    'é': 130, 'è': 138, 'ê': 136, 'ë': 137,
                    'à': 133, 'â': 131, 'ä': 132,
                    'ù': 151, 'û': 150, 'ü': 129,
                    'ô': 147, 'ö': 148, 'ò': 149,
                    'î': 140, 'ï': 139, 'ì': 141,
                    'ç': 135, 'Ç': 128,
                    'É': 144, 'È': 210, 'Ê': 210,
                    'À': 183, 'Â': 182,
                    'Ù': 235, 'Û': 234,
                    'Ô': 212,
                    'Î': 215,
                    '€': 213,
                    '°': 248, '²': 253,
                    '·': 250, '—': 196,
                };
                bytes.push(map[char] || 63); // 63 = '?'
            }
        }
        return new Uint8Array(bytes);
    },

    // Formater un ticket pour 58mm (32 colonnes)
    formatReceipt(data) {
        const w = 32;
        const sep = '='.repeat(w);
        const dash = '-'.repeat(w);
        let lines = [];

        // Init imprimante
        lines.push('\x1B\x40');

        // Centrer le texte
        const center = (text, pad = ' ') => {
            const t = text.trim();
            if (t.length >= w) return t.substring(0, w);
            const left = Math.floor((w - t.length) / 2);
            return pad.repeat(left) + t + pad.repeat(w - left - t.length);
        };

        const left = (text) => {
            const t = text.trim().substring(0, w);
            return t + ' '.repeat(w - t.length);
        };

        // En-tête
        lines.push('\x1B\x61\x01'); // Centrer
        lines.push('\x1B\x21\x30'); // Taille double hauteur
        lines.push(center('KONE SERVICES'));
        lines.push('\x1B\x21\x00'); // Taille normale
        lines.push(center('-----------------------'));
        lines.push(center('Tel: 73 32 64 00 / 66 16 05 05'));
        lines.push(center(sep));

        // Type de transaction
        lines.push('\x1B\x61\x01');
        lines.push('\x1B\x21\x10'); // Gras
        lines.push(center((data.type || '').toUpperCase()));
        lines.push('\x1B\x21\x00');
        lines.push(center(dash));

        // Détails
        lines.push('\x1B\x61\x00'); // Gauche
        lines.push(left('Operateur: ' + (data.operateur_money || data.operateur || '')));
        lines.push(left('Client: ' + (data.nom_client || data.client || '')));
        if (data.montant) {
            lines.push('\x1B\x61\x01');
            lines.push('\x1B\x21\x30'); // Double hauteur
            lines.push(center(data.montant + ' FCFA'));
            lines.push('\x1B\x21\x00');
        }
        lines.push('\x1B\x61\x00');
        lines.push(left('Reference: ' + (data.reference || '').substring(0, 12)));
        if (data.date) lines.push(left('Date: ' + data.date));
        if (data.heure) lines.push(left('Heure: ' + data.heure));
        lines.push(center(sep));

        // Pied de page
        lines.push('\x1B\x61\x01');
        lines.push(center('MERCI POUR VOTRE CONFIANCE'));
        lines.push(center(''));
        lines.push('\x1B\x61\x00');

        // Coupe papier (3 lignes + coupe)
        const cut = '\n'.repeat(4) + '\x1D\x56\x00';

        return lines.join('\n') + cut;
    },

    // Imprimer sur Bluetooth
    async print(data) {
        if (!this.connected || !this.characteristic) {
            throw new Error('Imprimante non connectée');
        }

        const ticket = this.formatReceipt(data);
        const encoder = new TextEncoder();
        const rawData = this._encodeText(ticket);

        // Envoyer par paquets de 512 octets
        const mtu = 512;
        for (let i = 0; i < rawData.length; i += mtu) {
            const chunk = rawData.slice(i, Math.min(i + mtu, rawData.length));
            await this.characteristic.writeValue(chunk);
        }

        return true;
    },

    // Imprimer via Web Share (fallback iOS/autres)
    async printViaShare(data) {
        const text = this._formatShareText(data);
        try {
            await navigator.share({ title: 'Reçu KONE SERVICES', text: text });
            return true;
        } catch (e) {
            if (e.name !== 'AbortError') throw e;
            return false;
        }
    },

    // Formater texte pour partage
    _formatShareText(data) {
        const sep = '====================';
        return [
            'KONE SERVICES',
            'Tel: 73 32 64 00',
            sep,
            (data.type || '').toUpperCase(),
            sep,
            'Operateur: ' + (data.operateur_money || data.operateur || ''),
            'Client: ' + (data.nom_client || data.client || ''),
            'Montant: ' + (data.montant || '') + ' FCFA',
            'Ref: ' + (data.reference || '').substring(0, 12),
            sep,
            'MERCI POUR VOTRE CONFIANCE',
        ].join('\n');
    },

    // Méthode principale : imprime ou partage selon le support
    async printReceipt(reference) {
        // Charger les données de la transaction
        const resp = await fetch('/impression-recu/' + reference + '/?format=json');
        const data = await resp.json();

        if (this.isSupported()) {
            // Android Chrome -> Web Bluetooth
            try {
                if (!this.connected) {
                    await this.connect();
                }
                await this.print(data);
                return { method: 'bluetooth', success: true };
            } catch (e) {
                console.warn('Bluetooth échoué, fallback PDF:', e);
                // Fallback: ouvrir et imprimer
                this._fallbackPrint(reference);
                return { method: 'fallback', success: true };
            }
        } else if (this.canShare()) {
            // iOS -> Web Share
            await this.printViaShare(data);
            return { method: 'share', success: true };
        } else {
            // Desktop ou autre -> fallback
            this._fallbackPrint(reference);
            return { method: 'fallback', success: true };
        }
    },

    // Fallback: ouvre la popup d'impression navigateur
    _fallbackPrint(reference) {
        const printWindow = window.open('/impression-recu/' + reference + '/', '_blank', 'width=400,height=600');
        if (printWindow) {
            printWindow.onload = function() {
                setTimeout(function() { printWindow.print(); }, 500);
            };
        } else {
            window.open('/impression-recu/' + reference + '/', '_blank');
        }
    },

    // Vérifier si une imprimante Bluetooth est déjà connectée
    async reconnect() {
        const saved = localStorage.getItem('kone_bluetooth_printer');
        if (saved && this.isSupported()) {
            try {
                // Web Bluetooth ne permet pas la reconnexion automatique
                // L'utilisateur doit scanner à nouveau
                return false;
            } catch (e) {
                return false;
            }
        }
        return false;
    }
};
