# Introduzione
Viste le limitazioni della mitigazione attuale, una possibile mitigazione alternativa potrebbe essere la seguente modifica alla macchina a stati. L'idea principale è quella di far si che lo zombie vada a rispondere allo stesso modo sia quando i cookie sono presenti, che quando non ci sono.

Ricordiamo che l'attaccante invia un `SYN` con un certo numero di sequenza al fine di creare una connessione semi-aperta che risiederà nel backlog. Supponiamo che il numero di sequenza sia 100. Successivamente, per verificare se il cookie è ancora presente, invierà un'ulteriore `SYN` con un numero di sequenza inferiore a quello precedente (es. 90, ma anche 99 come fatto nel codice python dell'attacco). Lo zombie risponderà nei due modi già visti:
- con un `SYN-ACK` se la connessione semiaperta del canary è stata evicted
- con un "challenge" `ACK` se la connessione semiaperta del canary è presente, il quale userà il sequence number del secondo `SYN` inviato dall'attaccante. Questo accade in quanto lo zombie può essere in solamente in `SYN-RECEIVED`. Ne consegue che passiamo direttamente ad [Other States (3.10.7.4)](https://datatracker.ietf.org/doc/html/rfc9293#name-other-states), in qui falliranno tutti i test di accettabilità, cosa che ci porterà allo step `If an incoming segment is not acceptable, an acknowledgment should be sent in reply`, per cui manderemo l'`ACK` e ignoreremo il segmento ricevuto. Questo esempio è anche riportato in [Figure 8: Recovery from Old Duplicate SYN](https://datatracker.ietf.org/doc/html/rfc9293#name-recovery-from-old-duplicate) 

# Spiegazione Funzionamento
La mitigazione vuole, quindi, rendere il comportamento del server del tutto indistinguibile agli occhi dell'attaccante, indipendentemente dalla presenza o meno della connessione semi-aperta (il canary) nel backlog. Per farlo è necessario aggiornare il comportamento della macchina a stati: se il server si trova in `SYN-RECEIVED` e riceve un `SYN` inatteso (es. un `SYN` con sequence number diverso), non genererà più un challenge `ACK`: il server dovrà sovrascrive i parametri della TCB attuale con le informazioni del nuovo `SYN` appena ricevuto per poi inviare un `SYN-ACK` in cui il sequence number "ACKppato" corrisponde al sequence number di questo ultimo `SYN` +1.

In questo modo, se l'attaccante invia un `SYN 90` per sondare la presenza del canary `SYN 100`, riceverà un `SYN-ACK` con `ACK=91`, impedendogli di dedurre la presenza.

## Analisi Problematiche per i Client Legittimi
Questa mitigazione sacrifica i meccanismi di protezioni dai pacchetti ritardati/duplicati per ottenere una maggiore sicurezza contro questo attacco di side-channel. Usando le seguenti assunzioni, vediamo come l'aggiornamento della TCB interferisca con un client legittimo:
- l'`ISS` del client è `ISS_C = 100`
- l'`ISS` del server è `ISS_S = 300`
- il `SYN` inviato dal client ha sequence number `100`
- il `SYN` duplicato ha sequence number `90`
- i `SYN` usano un singolo numero di sequenza (fanno avanzare `RCV.NXT` di uno, es. da `90` a `91`)

I casi possibili sono quindi:
- **Il server riceve prima `SYN 90`, poi `SYN 100`; il client riceve prima `SYN-ACK 90`, poi `SYN-ACK 100`** 
  Il server elabora il `SYN 90`, va in `SYN-RECEIVED` (`RCV.NXT=91`) e invia `SYN-ACK 90`. Riceve poi il `SYN 100` legittimo. Grazie alla mitigazione, il server sovrascrive la TCB impostando `RCV.NXT=101` e inviando il `SYN-ACK 100`. Il client, in `SYN-SENT` per 100, riceve il `SYN-ACK 90` (con `ACK=91`), rileva l'errore e invia un `RST` con `SEQ=91`. Tuttavia, poiché la TCB del server ora si aspetta 101 ed il `RST` (`91`) è fuori finestra, il server lo ignorerà. Subito dopo il client riceve il `SYN-ACK 100`, lo convalida, passa in `ESTABLISHED` e invia l'`ACK` finale (`101`) che il server accetterà. 
  **-> la modifica non impedisce la connessione**

- **Il server riceve prima `SYN 90`, poi `SYN 100`; il client riceve prima `SYN-ACK 100`, poi `SYN-ACK 90`** 
  Il server si comporta come sopra, ovvero sovrascrive la TCB in favore di `100`. Il client riceve il `SYN-ACK 100` legittimo, passa in `ESTABLISHED` e conclude l'handshake. Quando riceve il `SYN-ACK 90`, essendo già in `ESTABLISHED`, lo considererà come duplicato/fuori finestra risponderà "confermando" il proprio stato tramite un `ACK` senza altre conseguenze. 
  **-> la modifica non interferisce con il comportamento previsto.**

- **Il server riceve `SYN 100`, poi `SYN 90`; il client riceve prima `SYN-ACK 100`, poi un `SYN-ACK 90`**
  Il server riceve il `SYN 100` legittimo, va in `SYN-RECEIVED` (`RCV.NXT=101`) e genera `SYN-ACK 100`. Subito dopo riceve il vecchio `SYN 90` duplicato. A causa della mitigazione, il server sovrascrive la TCB valida con i dati del vecchio duplicato. Ne consegue che imposterà `RCV.NXT=91` e genererà `SYN-ACK 90`. Il client che riceve il `SYN-ACK 100` passa in `ESTABLISHED` e invia l'`ACK(101)` al server. Essendo che il server si aspetta `91`, alla ricezione dell'`ACK(101)` dal client lo valuterà come inaccettabile e invierà un `RST`.
  **-> la modifica causa il fallimento della connessione**

- **Il server riceve `SYN 100`, poi `SYN 90`; il client riceve prima l’`SYN-ACK 90` e poi il `SYN-ACK 100`** 
  Come nel caso precedente, il server sovrascrive la TCB e fissa il suo stato su `RCV.NXT=91`. Il client (che aspetta un riscontro per `100`) riceve per primo il `SYN-ACK 90` della mitigazione e, vedendo `ACK=91`, lo riconosce come errato e invia un `RST(91)`. Avendo il `RST` il sequence number "perfetto" per chiudere la connessione (si aspetta esattamente `91` come next), distruggerà immediatamente la connessione semi-aperta. Quando il client riceve poi il `SYN-ACK 100` legittimo e risponderà con `ACK(101)`, il server non avrà più entry nella TCB riguardante la connessione e risponderà con un ulteriore `RST`. 
  **-> la modifica porta al fallimento della connessione**


Vediamo quindi come, assumendo la presenza di pacchetti duplicati, è possibile che un client legittimo sia costretto a riaprire la connessione. Questo potrebbe non essere problematico nel caso in cui l'utente possa richiedere la risorsa (quindi aprendo una nuova connessione) o il programma usato ritenti per un certo numero di volte a reinstaurare il collegamento.