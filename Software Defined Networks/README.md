# Projeto SDN com P4

## Introdução
Este projeto tem como objetivo explorar conceitos de Redes Definidas por Software (SDN) utilizando a linguagem P4.

O projeto será desenvolvido como parte da disciplina de Redes Definidas por Software.

## Objetivos
- Introduzir e praticar a linguagem P4.
- Compreender os conceitos de plano de controle e plano de dados em SDN.
- Criar e testar funcionalidades de rede programáveis num ambiente simulado.

---

## Validação e Testes de Funcionalidades

Para garantir que o plano de dados (switch P4) e o plano de controlo (controlador SDN) operam conforme os requisitos do projeto, preparámos os seguintes cenários de teste:

### 1. Teste de Contagem de Pacotes (Telemetria)
**Objetivo:** Validar se os contadores (*Counters*) implementados no switch estão a registar corretamente o tráfego que atravessa o *pipeline*, essencial para a monitorização da rede.

1. Num terminal do nó de destino (ex: `h4`), inicie um servidor à escuta no porto UDP 5001:
   
```bash
   nc -u -l -p 5001
```

2. Num terminal do nó de origem (ex: `h1`), utilize um script em Python para gerar e enviar exatamente 10 pacotes UDP de 100 bytes:
   
```bash
   python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); [s.sendto(b'X'*100, ('10.0.2.4', 5001)) for _ in range(10)]"
```

**Resultado Esperado:** O controlador (no módulo de contagem) deverá reportar o incremento exato de 10 pacotes e os respetivos bytes processados para a fatia (*Slice*) correspondente à origem.

### 2. Teste de Network Slicing e Controlo de Débito (Meters)
**Objetivo:** Verificar se os medidores (*Meters*) estão a policiar corretamente a largura de banda de acordo com os limites estipulados para cada *Slice* (ex: Bronze, Silver, Gold).

1. No terminal do Mininet, abra as consolas dos hosts de origem e destino (ex: `h3` que pertence à fatia Gold, e `h4`):
   ```bash
   xterm h3 h4
   ```

2. No terminal do `h4` (Destino), inicie o servidor `iperf` em modo UDP, reportando a cada 1 segundo:
   ```bash
   iperf -s -u -i 1
   ```

3. No terminal do `h3` (Origem), inicie o cliente `iperf` tentando forçar o envio de tráfego a 27 Mbps durante 30 segundos:
   ```bash
   iperf -c 10.0.2.4 -u -b 27M -t 30
   ```

> **Resultado Esperado:** Os relatórios do servidor em `h4` e do módulo `slicing_counting` do controlador deverão comprovar que o débito útil (*BW Out*) estabiliza no limite configurado para a fatia Gold (ex: 25 Mbps), descartando o excesso (*Drops*).

### 3. Teste de Resiliência e Auto-Reparação (Self-Healing)
**Objetivo:** Demonstrar a capacidade do controlador de atuar perante falhas críticas no plano de dados. Este teste simula a perda acidental ou maliciosa de regras de encaminhamento L3 (`ipv4Lpm`), validando a rápida deteção e reinstalação automática das regras pelo controlador.

1. Noutro terminal do sistema, aceda à interface de linha de comandos (CLI) do simulador do switch (por defeito, o switch `d2` opera no porto 9091):
   ```bash
   simple_switch_CLI --thrift-port 9091
   ```

2. Visualize as regras de encaminhamento L3 atualmente ativas:
   ```bash
   table_dump MyIngress.ipv4Lpm
   ```

3. Force a falha, limpando completamente a tabela L3 (o tráfego será imediatamente interrompido):
   ```bash
   table_clear MyIngress.ipv4Lpm
   ```

> **Resultado Esperado:** O tráfego de rede (ex: do `iperf`) irá sofrer uma quebra momentânea. Quase em simultâneo, os *logs* do controlador reportarão a deteção da falha (`ENTRY_REMOVED`), procedendo de imediato à reposição do *pipeline* e reinstalação de todas as regras L3 e de Slicing. O tráfego deverá ser restabelecido com sucesso num intervalo de cerca de 3 segundos, e um novo `table_dump` confirmará a presença das rotas repostas.