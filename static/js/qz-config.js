// static/js/qz-config.js
window.QZConfig = {
    // Configuration de l'impression OPTIMISÉE
    printConfig: {
        encoding: 'CP850',
        size: { width: '58mm' },
        copies: 1,
        density: 15,  // DENSITÉ MAXIMALE (0-15) - 15 = plus foncé/lisible
        dotsPerLine: 576,  // Points par ligne pour 58mm
        dotsPerColumn: 8,
        dotPrintRatio: 100,  // Ratio d'impression max
        printingSpeed: 0,     // Vitesse lente pour meilleure qualité
        paperType: 0         // Papier thermique standard
    },
    
    // Commandes ESC/POS COMPLÈTES pour meilleure lisibilité
    escpos: {
        INIT: "\x1B\x40",                    // Réinitialiser imprimante
        CUT: "\x1D\x56\x41",                // Couper papier
        CUT_PARTIAL: "\x1D\x56\x41",        // Coupe partielle
        
        // Commandes de formatage
        BOLD_ON: "\x1B\x45\x01",            // Gras ON
        BOLD_OFF: "\x1B\x45\x00",           // Gras OFF
        UNDERLINE_ON: "\x1B\x2D\x01",       // Souligné ON
        UNDERLINE_OFF: "\x1B\x2D\x00",      // Souligné OFF
        
        // Alignements
        ALIGN_CENTER: "\x1B\x61\x01",       // Centrer
        ALIGN_LEFT: "\x1B\x61\x00",         // Gauche
        ALIGN_RIGHT: "\x1B\x61\x02",        // Droite
        
        // Tailles de police
        FONT_NORMAL: "\x1D\x21\x00",        // Taille normale
        FONT_DOUBLE_HEIGHT: "\x1D\x21\x01", // Double hauteur
        FONT_DOUBLE_WIDTH: "\x1D\x21\x10",  // Double largeur
        FONT_DOUBLE_SIZE: "\x1D\x21\x11",   // Double hauteur + largeur
        
        // Densité d'impression (TRÈS IMPORTANT)
        DARKER: {
            LEVEL_1: "\x1D\x73\x01",        // Plus clair
            LEVEL_2: "\x1D\x73\x02",        // Normal
            LEVEL_3: "\x1D\x73\x03",        // Plus foncé
            LEVEL_4: "\x1D\x73\x04",        // Très foncé (MAX)
        },
        
        // Hauteur des caractères
        CHARACTER_HEIGHT: {
            NORMAL: "\x1B\x21\x00",         // Normal
            TALL: "\x1B\x21\x10",           // Grand
        },
        
        // Commandes de qualité
        QUALITY_HIGH: "\x1D\x28\x45\x04\x00\x02\x01",  // Haute qualité
        QUALITY_NORMAL: "\x1D\x28\x45\x04\x00\x02\x00", // Qualité normale
        
        // Espacement
        LINE_SPACING: {
            DEFAULT: "\x1B\x32",            // Espacement par défaut
            SMALL: "\x1B\x33\x18",          // Petit espacement
            NORMAL: "\x1B\x33\x24",         // Normal
            LARGE: "\x1B\x33\x30",          // Grand espacement
        }
    },
    
    // Formatage des tickets avec caractères lisibles
    receiptTemplate: {
        width: 32,
        // Conversion des caractères spéciaux
        charMap: {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ô': 'o', 'ö': 'o',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n',
            '€': 'EUR', '$': 'USD',
        },
        // Caractères recommandés (plus lisibles)
        recommendedChars: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -./',
        // Remplacer les caractères problématiques
        replaceMap: {
            'œ': 'oe', 'æ': 'ae', 'ß': 'ss'
        }
    },
    
    // Configuration spécifique pour QZ Tray
    qzSettings: {
        retryInterval: 2000,
        maxRetries: 5,
        timeout: 30000,
        // Forcer le mode raw pour meilleure qualité
        forceRaw: true,
        // Imprimer en haute qualité
        highQuality: true
    }
};

// Fonction utilitaire pour nettoyer et optimiser le texte avant impression
function cleanPrintText(text, width = 32) {
    if (!text) return '';
    
    let cleaned = text;
    
    // Remplacer les caractères spéciaux
    for (let [key, value] of Object.entries(window.QZConfig.receiptTemplate.charMap)) {
        cleaned = cleaned.replace(new RegExp(key, 'g'), value);
    }
    
    for (let [key, value] of Object.entries(window.QZConfig.receiptTemplate.replaceMap)) {
        cleaned = cleaned.replace(new RegExp(key, 'g'), value);
    }
    
    // Supprimer les caractères non imprimables
    cleaned = cleaned.replace(/[^\x20-\x7E\n\r]/g, ' ');
    
    // Nettoyer les lignes trop longues
    const lines = cleaned.split('\n');
    const wrappedLines = [];
    
    for (let line of lines) {
        while (line.length > width) {
            wrappedLines.push(line.substring(0, width));
            line = line.substring(width);
        }
        wrappedLines.push(line);
    }
    
    return wrappedLines.join('\n');
}

// Configuration imprimante par type
const PrinterProfiles = {
    '58mm': {
        width: 32,
        fontSize: 1,
        lineSpacing: 30,
        density: 15
    },
    '80mm': {
        width: 48,
        fontSize: 1,
        lineSpacing: 30,
        density: 15
    }
};