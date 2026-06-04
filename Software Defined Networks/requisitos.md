# Requisitos do Sistema — Dynamic Network Slicing

## 1. Requisitos Funcionais

### 1.1 Classificação de Slice
O sistema deve ser capaz de identificar a slice de cada pacote com base em critérios como:
- Endereço IP de origem/destino
- Porta de transporte (ex: aplicações)
- Outros critérios definidos pelo operador

A classificação deve ser configurável em runtime.

---

### 1.2 Encapsulamento / Decapsulamento
- Inserção de um **Slice Header customizado** no ingress gateway
- Remoção do header no egress gateway

O header deve incluir:
- Slice ID
- Classe de prioridade (ex: gold, silver, bronze)
- Outros campos relevantes (flags, metadata)

---

### 1.3 Forwarding consciente da Slice
As decisões de encaminhamento devem considerar o Slice ID:
- Diferentes slices podem seguir caminhos distintos
- Deve ser possível alterar caminhos dinamicamente

---

### 1.4 Isolamento de Slice
O sistema deve garantir isolamento entre slices:
- Uma slice não pode consumir recursos de outra
- O plano de dados deve detetar tráfego acima da quota
- Tráfego excedente deve ser marcado ou desviado

---

### 1.5 Traffic Shaping
O tráfego acima da quota deve ser tratado por uma **cNF (container)**:
- Queueing
- Delay
- Drop
- Re-marking

Nota: Este processamento não pode ser implementado apenas em P4.

---

### 1.6 Contagem por Slice
O sistema deve manter contadores de:
- Número de pacotes
- Número de bytes

Separados por:
- Slice
- Classe de prioridade

---

### 1.7 Reconfiguração dinâmica
Deve ser possível, em runtime:
- Alterar a atribuição de slices
- Modificar prioridades
- Alterar caminhos de forwarding

Sem reiniciar a rede.

---

### 1.8 Forwarding base

#### L2 Forwarding
- Encaminhamento baseado em MAC address
- Pode ser estático ou dinâmico

#### L3 Forwarding
- Encaminhamento entre subnets baseado em IP

---

## 2. Requisitos de Topologia

A topologia deve incluir:
- Pelo menos 4 dispositivos P4
  - ≥ 1 switch L2
  - ≥ 1 router L3
- Pelo menos 2 subnets
- Pelo menos 6 hosts
- Pelo menos 2 slices distintas

---

### 2.1 cNF (Container Network Function)
- Pelo menos 1 container
- Ligação via interface `veth` a um switch P4
- Comunicação exclusivamente via pacotes (sem ligação direta ao controller)

---

### 2.2 Plano de Controlo
- Todos os dispositivos devem ser geridos via **P4Runtime controller**

---

## 3. Requisitos Dinâmicos

### 3.1 Reação à congestão
Quando uma slice excede a sua capacidade, o sistema deve:
- Reroute de tráfego
- Redução de prioridade
- Limitação de taxa (via cNF)

Sem intervenção manual.

---

### 3.2 Diferenciação de slices
O sistema deve suportar pelo menos 3 slices:
- Gold (alta prioridade)
- Silver (prioridade intermédia)
- Bronze (best effort)

Cada slice deve ter tratamento diferenciado:
- Caminhos distintos e/ou
- Prioridades distintas e/ou
- Limites de taxa distintos

---

### 3.3 Configuração em runtime
- Alterações devem ser feitas sem reiniciar a rede
- Implementadas via controller (P4Runtime)

---

## 4. Requisitos Arquiteturais

### 4.1 P4 Data Plane
Responsável por:
- Parsing de headers
- Match-action
- Encapsulamento/decapsulamento
- Forwarding

Limitações:
- Expressividade limitada
- Sem suporte avançado de filas

---

### 4.2 cNF (Container)
Responsável por:
- Traffic shaping
- Queueing e buffering
- Rate limiting
- Processamento stateful

---

### 4.3 Controller
Responsável por:
- Visão global da rede
- Instalação e remoção de regras
- Monitorização de contadores
- Reconfiguração dinâmica

---

## 5. Restrições

- Deve ser seguida a estrutura do projeto:
- p4/
- controller/plugins/
- controller/resources/
- mininet/
- run_sim.sh
- cNFs:
- Não podem comunicar diretamente com o controller

- Todo o sistema deve suportar operação dinâmica

---

## 6. Resumo

O sistema deve implementar:
- Network slicing com isolamento
- Header customizado para slices
- Forwarding dependente da slice
- Controlo de recursos por slice
- Adaptação dinâmica à carga

Integrando:
- P4 (data plane)
- Controller (control plane)
- cNF (processamento avançado)