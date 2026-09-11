Raccolta di formule estratte dalla tesi al fine di effettuare l'analisi statistica
## Miscellaneous 
#### Pacchetti SYN per arrivare alla threshold
Calcola il numero di pacchetti SYN inviati dall'attaccante per riempire la coda:
$$N = \frac{3}{4} \cdot B_{\text{guess}}$$
- **$N$**: Numero totale di pacchetti inviati.
- **$B_{\text{guess}}$**: Dimensione presunta (assunta dall'attaccante) del backlog (coda).

#### Descrizione pacchetti
- **Pacchetti Spoofed:** Pacchetti spoofati in cui la sorgente appare essere la vittima (inviati in quantità pari a $\frac{3}{8}B$)
- **Pacchetti Canary:** pacchetti "canarino" inviati dall'attaccante allo zombie per monitorare lo stato della coda (inviati in quantità pari a $\frac{3}{8}B$)

---

## Formule usate per la scelta della soglia nel Kernel
#### Limite inferiore soglia
$$\text{base\_threshold} = \text{backlog\_size} \cdot \frac{3}{8}$$
#### Range di estrazione della soglia
$$\text{range} = \left(\text{backlog\_size} \cdot \frac{6}{8}\right) + 1 - \text{base\_threshold}$$
#### Estrazione effettiva
Calcolo della nuova soglia di _eviction_ casuale per contrastare l'inferenza dell'attaccante:
$$\text{sk\_max\_ack\_backlog\_custom} = (\text{random\_num} \bmod (\text{range} + 1)) + \text{base\_threshold}$$
-> è tutto documentato direttamente nel codice in `Vagrant/zombie_files/kernel/net/ipv4/inet_connection_sock.c` a riga 1192.
  

  ---

## Analisi probabilistica (capitolo 4.2)
### Probabilità di selezione una soglia uguale
$$P_s = \frac{1}{\left(\frac{6}{8} - \frac{3}{8}\right) \cdot \text{backlog\_size} + 2} = \frac{1}{\frac{3}{8} \cdot \text{backlog\_size} + 2}$$

  
### Valori limite per la soglia di eviction
$$T_{\min}(B) = \left\lfloor \frac{3}{8} B \right\rfloor \quad \text{e} \quad T_{\max}(B) = \left\lfloor \frac{6}{8} B \right\rfloor + 1$$
-> nota: con $T_n$ indicheremo la threshold <u>reale</u> a tempo $n$


### Dimensione della window
$$w(B) = T_{\max}(B) - T_{\min}(B) + 1$$

  
### Spazio campionario totale
Scelta del kernel per scelta dell'attaccante. 
$$\text{Spazio Campionario Totale} = w(B)^2$$
-> Reminder che la soglia viene cambiata dopo che l'attaccante ha trovato la threshold con la prima parte dell'attacco, ovvero $T_{n−1} \cdot T_n$ con $T_n$ la threshold a tempo $n$.
  

### Numero di pacchetti inviati a tempo $n$
Inviamo lo stesso numero di pacchetti canary e di connessioni spoofed, quindi:
$$C_n = S_n = \frac{3}{4} B \cdot \frac{1}{2} = \left(\frac{3}{4} B\right ) \cdot \frac{1}{2} = \left( T_{n-1} \right) \cdot \frac{1}{2}$$
-> nel complesso inviamo $C_n+S_n= T_{n-1}$ pacchetti
-> indichiamo con $C_n^\prime$ e $S_n^\prime$ i pacchetti che sopravvivono nella coda a tempo $n$
  
---
  
## Condizioni necessarie per ogni caso (capitolo 4.2.2)
Come variabili/stati/condizioni abbiamo:
- $D_p$ rilevamento **positivo/alive** ($C^\prime_n + S^\prime_n < T_n$)
- $D_n$ rilevamento **negativo/not-alive** ($C^\prime_n + S^prime_n \ge T_n$)
- $P$ target **effettivamente alive** ($S^\prime_n = 0\; C^\prime_n = C_n$)
- $N$ target **effettivamente not-alive** ($S^\prime_n = S_n\; C^\prime_n = C_n$)
- $C_n+S_n$ numero di pacchetti canary+spoofed <u>inviati</u> a tempo $n$
- $C^\prime_n+S^\prime_n$ numero di pacchetti canary+spoofed <u>in coda</u> a tempo $n$
- $T_n/T_{n-1}$ indicheremo la threshold <u>reale</u> a tempo $n/n-1$



| **Caso**           | **Condizione Logica** | **Relazione Matematica**                          | **Descrizione**                           |
| ------------------ | --------------------- | ------------------------------------------------- | ----------------------------------------- |
| **Falso Negativo** | $D_n \land P$         | $C'_n + S'_n = C_n = \frac{1}{2} T_{n-1} \ge T_n$ | Target VIVO classificato come OFFLINE     |
| **Vero Negativo**  | $D_n \land N$         | $C'_n + S'_n = 2C_n = T_{n-1} \ge T_n$            | Target OFFLINE correttamente classificato |
| **Falso Positivo** | $D_p \land N$         | $C'_n + S'_n = 2C_n = T_{n-1} < T_n$              | Target OFFLINE classificato come VIVO     |
| **Vero Positivo**  | $D_p \land P$         | $C'_n + S'_n = C_n = \frac{1}{2} T_{n-1} < T_n$   | Target VIVO correttamente classificato    |

## Calcolo numero di occorrenze effettive per caso
### Occorrenze per i falsi positivi $n(F\;P)$
Target not-alive classificato come alive, ovvero quando i pacchetti inviati non sono sufficienti a causare un'eviction, ovvero quando $T_{n-1}<T_n$. Se ora contassimo tutti i casi in cui accade otterremmo:
$$n(\text{FP}) = \sum_{w = T_{\min}}^{T_{\max}} \sum_{n = w+1}^{T_{\max}} 1$$
### Occorrenze per i falsi negativi $n(F\;N)$
Target alive classificato come not-alive, ovvero quando $T_{n-1}\ge \lfloor \frac{3}{8}B \rfloor$ (canary rimossi), quindi $\frac{1}{2}T_{n-1}\ge T_n\; \Rightarrow\; 2\cdot T_n\le T_{n-1}$, ovvero la threshold nuova è stata più che dimezzata per far apparire il target come non attivo andando a rimuovere i canary.
La condizione $\frac{1}{2}T_{n-1}\ge T_n$ accade quando $T_{n-1}\in[\frac{3}{4}B, T_{n-1}]$, quindi i casi associati ad ogni stato $T_{n-1}$ sono $C_n-1-T_{min}(B)+1$ visto che i canary da inviare devono essere $\ge T_{min}(B)$ per causare un'eviction.
$$
\begin{aligned}
n(\text{FN}) &= \sum_{w = \left\lfloor \frac{3}{4} B \right\rfloor}^{T_{\max}} (C_w - T_{\min}(B) + 1) \\ \\
&= \sum_{w = \left\lfloor \frac{3}{4} B \right\rfloor}^{T_{\max}} \left( \frac{1}{2}w - T_{\min}(B) + 1 \right)
\end{aligned}
$$
### Occorrenze per i veri positivi $n(T\;P)$
$$
w(B)^2 - n(F\;P)
$$
### Occorrenze per i veri negativi $n(T\;F)$
$$
w(B)^2 - n(F\;N)
$$

  
### Riassumendo le formule
Di seguito una tabella riassuntiva come riportato nella tesi

|                      | **Classificazione Alive**                                                   | **Classificazione Not-Alive**                                                                                                 |
| -------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Target Alive**     | $\frac{w(B)^2 - n(F\;N)}{w(B)^2}$                                           | $\frac{\sum_{w = \left\lfloor \frac{3}{4} B \right\rfloor}^{T_{\max}} \left( \frac{1}{2}w - T_{\min}(B) + 1 \right)}{w(B)^2}$ |
| **Target Not-Alive** | $\frac{\sum_{w = T_{\min}}^{T_{\max}} \sum_{n = w+1}^{T_{\max}} 1}{w(B)^2}$ | $\frac{w(B)^2 - n(F\;N)}{w(B)^2}$                                                                                             |

  ---

## Applicazione formule per trovare errori migliori
Al fine di trovare dei valori per le soglie della window, possiamo fare uno sweep su tutti i valori possibili assumibili dalle soglie della window, calcolare per tutte le soglie la coppia che da tutte le probabilità più vicine a $0.5$ per la data backlog size e plottare quanto ottenuto. Così facendo evitiamo di dover studiare le funzioni sfruttando il fatto che siamo in ambito discreto con uno spazio campionario molto piccolo da esplorare.

Al fine di fare la scelta che più permette a tutte le probabilità di avvicinarsi al $50\%$, possiamo minimizzare la "distanza" che ogni probabilità ha da $0.5$, ovvero minimizzando $\sum_{probabilities} (p-0.5)^2$

Otteniamo quindi il seguente grafico, il quale illustra come aumentare la backlog size vada a far avvicinare al $50\%$ le probabilità per un client effettivamente not-alive, mentre un client alive diventa mano a mano sempre più evidente all'attaccante del fatto che sia attivo. Questo è riflesso anche dai calcoli analitici e sperimentali effettuati dalla tesi.
![[PlotProbVsBacklog.png]]