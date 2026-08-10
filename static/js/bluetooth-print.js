const KONEPrint = (function() {
    let state = {
        connected: false,
        device: null,
        server: null,
        service: null,
        characteristic: null,
        connectionType: null, // 'ble', 'usb', 'serial'
    };

    function isBluetoothSupported() {
        return !!navigator.bluetooth;
    }

    function isWebUsbSupported() {
        return !!navigator.usb;
    }

    function isWebSerialSupported() {
        return !!navigator.serial;
    }

    function isMobile() {
        return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    }

    function isIOS() {
        return /iPhone|iPad|iPod/i.test(navigator.userAgent);
    }

    function canShareFile() {
        return !!navigator.share && /Android/i.test(navigator.userAgent);
    }

    function encodeCP437(text) {
        const bytes = [];
        for (const ch of text) {
            const code = ch.charCodeAt(0);
            if (code < 128) {
                bytes.push(code);
            } else {
                const map = {
                    'é':130,'è':138,'ê':136,'ë':137,'à':133,'â':131,'ä':132,
                    'ù':151,'û':150,'ü':129,'ô':147,'ö':148,'ò':149,
                    'î':140,'ï':139,'ì':141,'ç':135,'Ç':128,
                    'É':144,'È':210,'Ê':210,'À':183,'Â':182,
                    'Ù':235,'Û':234,'Ô':212,'Î':215,
                    '€':213,'°':248,'²':253,'·':250,'—':196,
                };
                bytes.push(map[ch] || 63);
            }
        }
        return new Uint8Array(bytes);
    }

    function buildEscPosTicket(data) {
        const W = 32;
        const sep = '='.repeat(W);
        const dash = '-'.repeat(W);

        function center(t) {
            const s = String(t).trim();
            if (s.length >= W) return s.slice(0, W);
            const pad = Math.floor((W - s.length) / 2);
            return ' '.repeat(pad) + s + ' '.repeat(W - pad - s.length);
        }

        function left(t) {
            const s = String(t).trim().slice(0, W);
            return s + ' '.repeat(W - s.length);
        }

        const lines = [];

        // Init
        lines.push('\x1B\x40');
        // Header center
        lines.push('\x1B\x61\x01');
        lines.push('\x1B\x21\x10');
        lines.push(center('KONE SERVICES'));
        lines.push('\x1B\x21\x00');
        lines.push(center('Services Transfert'));
        lines.push(center('Tel: 76 89 77 31'));
        lines.push(center(sep));

        // Type
        lines.push('\x1B\x21\x10');
        lines.push(center(String(data.type || '').toUpperCase()));
        lines.push('\x1B\x21\x00');
        lines.push(center(dash));

        // Details
        lines.push('\x1B\x61\x00');
        lines.push(left('Agent: ' + (data.operateur || data.agent || '-')));
        lines.push(left('Operateur: ' + (data.operateur_money || '-')));
        if (data.nom_client || data.client) {
            lines.push(left('Client: ' + (data.nom_client || data.client)));
        }
        if (data.numero_client || data.numero) {
            lines.push(left('Tel: ' + (data.numero_client || data.numero)));
        }
        lines.push(center(dash));
        if (data.montant) {
            lines.push('\x1B\x61\x01');
            lines.push('\x1B\x21\x30');
            lines.push(center(data.montant + ' FCFA'));
            lines.push('\x1B\x21\x00');
            lines.push(center(dash));
        }
        lines.push('\x1B\x61\x00');
        lines.push(left('Ref: ' + String(data.reference || data.ref || '').slice(0, 14)));
        if (data.date) lines.push(left('Date: ' + data.date));
        if (data.heure) lines.push(left('Heure: ' + data.heure));
        if (data.frais) lines.push(left('Frais: ' + data.frais + ' FCFA'));

        lines.push(center(sep));
        lines.push('\x1B\x61\x01');
        lines.push(center('MERCI'));
        lines.push(center(''));

        // Coupe
        lines.push('\x1B\x61\x00');
        for (let i = 0; i < 5; i++) lines.push('');
        lines.push('\x1D\x56\x00');

        return lines.join('\n');
    }

    // ---- Web Bluetooth (BLE) ----
    async function connectBLE() {
        const device = await navigator.bluetooth.requestDevice({
            acceptAllDevices: true,
            optionalServices: [
                '00001101-0000-1000-8000-00805f9b34fb', // SPP
                '000018f0-0000-1000-8000-00805f9b34fb', // Standard Printer
                '00001812-0000-1000-8000-00805f9b34fb', // HID
            ],
        });

        state.device = device;
        device.addEventListener('gattserverdisconnected', () => {
            state.connected = false;
            state.device = null;
            state.server = null;
            state.service = null;
            state.characteristic = null;
        });

        state.server = await device.gatt.connect();
        state.connected = true;

        // Try known services
        const sppUUID = '00001101-0000-1000-8000-00805f9b34fb';
        const prnUUID = '000018f0-0000-1000-8000-00805f9b34fb';

        let characteristic = null;
        try {
            const svc = await state.server.getPrimaryService(sppUUID);
            const chars = await svc.getCharacteristics();
            for (const c of chars) {
                if (c.properties.write || c.properties.writeWithoutResponse) {
                    characteristic = c;
                    state.service = svc;
                    break;
                }
            }
        } catch (_) {}

        if (!characteristic) {
            try {
                const svc = await state.server.getPrimaryService(prnUUID);
                const chars = await svc.getCharacteristics();
                for (const c of chars) {
                    if (c.properties.write || c.properties.writeWithoutResponse) {
                        characteristic = c;
                        state.service = svc;
                        break;
                    }
                }
            } catch (_) {}
        }

        // Scan all services
        if (!characteristic) {
            const services = await state.server.getPrimaryServices();
            for (const svc of services) {
                const chars = await svc.getCharacteristics();
                for (const c of chars) {
                    if (c.properties.write || c.properties.writeWithoutResponse) {
                        characteristic = c;
                        state.service = svc;
                        break;
                    }
                }
                if (characteristic) break;
            }
        }

        if (!characteristic) {
            throw new Error('Aucune caracteristique d\'ecriture trouvee sur cet appareil');
        }

        state.characteristic = characteristic;
        state.connectionType = 'ble';
    }

    async function sendViaBLE(data) {
        const mtu = 512;
        const raw = encodeCP437(data);
        for (let i = 0; i < raw.length; i += mtu) {
            const end = Math.min(i + mtu, raw.length);
            const chunk = raw.slice(i, end);
            if (state.characteristic.properties.writeWithoutResponse) {
                await state.characteristic.writeValueWithoutResponse(chunk);
            } else {
                await state.characteristic.writeValue(chunk);
            }
            // Petit delai entre les paquets
            await new Promise(r => setTimeout(r, 30));
        }
        return true;
    }

    // ---- Web USB ----
    async function connectUSB() {
        const device = await navigator.usb.requestDevice({ filters: [] });
        await device.open();
        if (device.configuration === null) {
            await device.selectConfiguration(1);
        }
        await device.claimInterface(0);
        state.device = device;
        state.connected = true;
        state.connectionType = 'usb';
    }

    async function sendViaUSB(data) {
        const raw = encodeCP437(data);
        const mtu = 64;
        for (let i = 0; i < raw.length; i += mtu) {
            const end = Math.min(i + mtu, raw.length);
            const chunk = raw.slice(i, end);
            await state.device.transferOut(1, chunk);
            await new Promise(r => setTimeout(r, 20));
        }
        return true;
    }

    // ---- Web Serial ----
    async function connectSerial() {
        const port = await navigator.serial.requestPort({});
        await port.open({ baudRate: 9600 });
        state.device = port;
        state.connected = true;
        state.connectionType = 'serial';
    }

    async function sendViaSerial(data) {
        const writer = state.device.writable.getWriter();
        const raw = encodeCP437(data);
        await writer.write(raw);
        writer.releaseLock();
        return true;
    }

    // ---- Public API ----
    return {
        isSupported() {
            // Detecte si au moins un moyen de connection est disponible
            return isBluetoothSupported() || isWebUsbSupported() || isWebSerialSupported();
        },

        canBluetooth() {
            return isBluetoothSupported();
        },

        canUSB() {
            return isWebUsbSupported();
        },

        canSerial() {
            return isWebSerialSupported();
        },

        isMobile() {
            return isMobile();
        },

        isConnected() {
            return state.connected;
        },

        async connect(type) {
            type = type || (isBluetoothSupported() ? 'ble' : isWebUsbSupported() ? 'usb' : 'serial');
            this.disconnect();
            switch (type) {
                case 'ble':
                    await connectBLE();
                    break;
                case 'usb':
                    await connectUSB();
                    break;
                case 'serial':
                    await connectSerial();
                    break;
                default:
                    throw new Error('Type de connexion inconnu: ' + type);
            }
            try {
                localStorage.setItem('kone_print_connection', JSON.stringify({
                    type: state.connectionType,
                    name: state.device.name || state.device.productName || 'Imprimante'
                }));
            } catch (_) {}
            return state.device.name || state.device.productName || 'Connecte';
        },

        disconnect() {
            try {
                if (state.device && state.connectionType === 'ble' && state.device.gatt) {
                    state.device.gatt.disconnect();
                }
                if (state.device && state.connectionType === 'usb') {
                    state.device.close();
                }
                if (state.device && state.connectionType === 'serial') {
                    state.device.close();
                }
            } catch (_) {}
            state.connected = false;
            state.device = null;
            state.server = null;
            state.service = null;
            state.characteristic = null;
            state.connectionType = null;
            try { localStorage.removeItem('kone_print_connection'); } catch (_) {}
        },

        formatReceipt(data) {
            return buildEscPosTicket(data);
        },

        async print(data) {
            if (!state.connected || (!state.characteristic && state.connectionType === 'ble')) {
                throw new Error('Imprimante non connectee');
            }
            const ticket = buildEscPosTicket(data);
            if (state.connectionType === 'ble') {
                return await sendViaBLE(ticket);
            }
            if (state.connectionType === 'usb') {
                return await sendViaUSB(ticket);
            }
            if (state.connectionType === 'serial') {
                return await sendViaSerial(ticket);
            }
            throw new Error('Aucune connexion active');
        },

        async printReceipt(reference) {
            const resp = await fetch('/impression-recu/' + String(reference) + '/?format=json');
            if (!resp.ok) throw new Error('Impossible de charger les donnees du recu');
            const data = await resp.json();

            // Essaie la connexion existante
            if (state.connected) {
                try {
                    await this.print(data);
                    return { method: state.connectionType, success: true };
                } catch (e) {
                    this.disconnect();
                    throw e;
                }
            }

            // Essaie Bluetooth BLE
            if (isBluetoothSupported()) {
                try {
                    await connectBLE();
                    await this.print(data);
                    return { method: 'ble', success: true };
                } catch (e) {
                    this.disconnect();
                }
            }

            // Internet Explorer / fallback: telechargement + partage
            const blob = await this.generateReceiptBlob(data);
            if (canShareFile()) {
                try {
                    const file = new File([blob], 'recu-' + reference + '.txt', { type: 'text/plain' });
                    await navigator.share({ files: [file], title: 'Recu KONE SERVICES' });
                    return { method: 'share', success: true };
                } catch (_) {}
            }

            // Fallback: ouvre dans le navigateur pour impression
            this.fallbackPrint(reference);
            return { method: 'fallback', success: true };
        },

        async generateReceiptBlob(data) {
            const ticket = buildEscPosTicket(data);
            return new Blob([ticket], { type: 'text/plain;charset=CP437' });
        },

        fallbackPrint(reference) {
            const win = window.open('/impression-recu/' + String(reference) + '/', '_blank', 'width=400,height=600');
            if (win) {
                win.onload = function() {
                    setTimeout(function() { win.print(); }, 500);
                };
            } else {
                window.open('/impression-recu/' + String(reference) + '/', '_blank');
            }
        },
    };
})();
