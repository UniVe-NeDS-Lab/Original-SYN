#!/bin/bash

# Nome del file di output
OUTPUT_FILE="128_2.txt"
i=1

# Ciclo infinito
while [ $i -le 50 ]; do
    # Esegui lo script Python e salva l'output nel file
    sudo python3 test128_2.py 192.168.5.100 8086 >> "$OUTPUT_FILE" 2>&1

    # (opzionale) Aggiungi una riga vuota per separare le esecuzioni
    echo "" >> "$OUTPUT_FILE"
    sleep 90

    ((i++))
done

