# Gestão Cooperativa de Tráfego em Zona de Obras com V2X
 
Simulação de um sistema cooperativo de gestão de tráfego em zonas de obras, baseado em comunicações V2X (ITS-G5), utilizando Eclipse MOSAIC e SUMO. Uma RSU dissemina recomendações dinâmicas de velocidade por zonas e os veículos cooperam via comunicação V2V multi-hop.
 
---
 
## Execução
 
### 1. Colocar a pasta do projeto em:
 
```
/opt/eclipse-mosaic-24.1/scenarios/
```
 
### 2. Executar a simulação
 
```bash
cd /opt/eclipse-mosaic-24.1/
./mosaic.sh -s <nome_do_cenario> -w 0
```