#!/bin/bash

# Nome del file di output
OUTPUT_FILE="alive_result_32.txt"
i=1

# Ciclo infinito
while [ $i -le 100 ]; do
    # Esegui lo script Python e salva l'output nel file
    sudo python3 ../main.py 192.168.4.100 8084 192.168.5.100 12 >> "$OUTPUT_FILE" 2>&1

    # (opzionale) Aggiungi una riga vuota per separare le esecuzioni
    echo "" >> "$OUTPUT_FILE"
    sleep 90

    ((i++))
done

