/* SPDX-License-Identifier: ANCL-1.0
 * Copyright (c) 2026  jfpereira <d12267@di.uminho.pt> — di.uminho.pt
 * Academic use only · no commercial use · see LICENSE
 * AI-assisted development: Claude (Anthropic)
 */

#include <core.p4>
#include <v1model.p4>
#include "headers.p4"

// CONSTs ***********************************************************************

const bit<8> PROTO_TCP = 0x06;
const bit<8> PROTO_UDP = 0x11;
const bit<9> LAN_PORT        = 1;
const bit<9> LAN_PORT2       = 2;
const bit<9> ARP_PROXY_PORT  = 3;
const bit<9> DHCP_SERVER_PORT_CNF = 4;       
const bit<16> DHCP_SERVER_PORT = 67;         
const bit<16> DHCP_CLIENT_PORT = 68;
const bit<9> TS_PORT         = 5;

#define BLOOM_FILTER_ENTRIES   4096
#define BLOOM_FILTER_BIT_WIDTH 1

header transport_t {
    bit<16> srcPort;
    bit<16> dstPort;
}

// STRUCTURES *******************************************************************

struct metadata {
    macAddr_t nextHopMac;
    bit<8>    slice_id;
}

struct headers {
    ethernet_t  ether;
    arp_t       arp;
    ipv4_t      ipv4;
    transport_t transport;
    udp_tail_t  udp_tail;
    dhcp_t      dhcp;
}

// PARSER ***********************************************************************

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ether);
        transition select(hdr.ether.type) {
            TYPE_IPV4: parse_ipv4;
            TYPE_ARP:  parse_arp;
            default:   accept;
        }
    }

    state parse_arp {
        packet.extract(hdr.arp);
        transition accept;
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            PROTO_TCP: parse_transport;
            PROTO_UDP: parse_udp;
            default:   accept;
        }
    }

    state parse_transport {
        packet.extract(hdr.transport);
        transition accept;
    }

    state parse_udp {
        packet.extract(hdr.transport);
        transition select(hdr.transport.dstPort) {
            DHCP_SERVER_PORT: skip_udp_tail;
            DHCP_CLIENT_PORT: skip_udp_tail;
            default:          accept;
        }
    }

    state skip_udp_tail {
        packet.extract(hdr.udp_tail);
        transition parse_dhcp;
    }

    state parse_dhcp {
        packet.extract(hdr.dhcp);
        transition accept;
    }
}

// CHECKSUM VERIFICATION ********************************************************

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply { }
}

// INGRESS **********************************************************************

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t std_meta) {

    register<bit<BLOOM_FILTER_BIT_WIDTH>>(BLOOM_FILTER_ENTRIES) bloomFilter1;
    register<bit<BLOOM_FILTER_BIT_WIDTH>>(BLOOM_FILTER_ENTRIES) bloomFilter2;

    bit<32> regPosOne;
    bit<32> regPosTwo;
    bit<1>  regValOne;
    bit<1>  regValTwo;

    counter(1, CounterType.packets_and_bytes) forwardedCounter;
    counter(1, CounterType.packets_and_bytes) droppedCounter;
    counter(4, CounterType.packets_and_bytes) sliceCounter;  
    counter(4, CounterType.packets_and_bytes) passedCounter; 
    meter(4, MeterType.bytes) sliceMeter;                    

    action set_slice(bit<8> slice_id) {
        meta.slice_id = slice_id;
        //sliceCounter.count((bit<32>)slice_id);
    }

    table slice_classifier {
        key = { hdr.ipv4.srcAddr: exact; }
        actions = { set_slice; NoAction; }
        size = 256;
        default_action = NoAction;
    }

    action drop() {
        mark_to_drop(std_meta);
        droppedCounter.count(0);
    }

    action computeHashes(ip4Addr_t ipSrc, ip4Addr_t ipDst,
                         bit<16> portSrc, bit<16> portDst) {
        hash(regPosOne, HashAlgorithm.crc16, (bit<32>)0,
             { ipSrc, ipDst, hdr.ipv4.protocol, portSrc, portDst },
             (bit<32>)BLOOM_FILTER_ENTRIES);
        hash(regPosTwo, HashAlgorithm.crc32, (bit<32>)0,
             { ipSrc, ipDst, hdr.ipv4.protocol, portSrc, portDst },
             (bit<32>)BLOOM_FILTER_ENTRIES);
    }

    action forward(bit<9> egressPort, macAddr_t nextHopMac) {
        std_meta.egress_spec = egressPort;
        meta.nextHopMac = nextHopMac;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    }

    table ipv4Lpm {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = {
            forward;
            drop;
        }
        size = 256;
        default_action = drop;
    }

    action rewriteMacs(macAddr_t srcMac) {
        hdr.ether.srcAddr = srcMac;
        hdr.ether.dstAddr = meta.nextHopMac;
    }

    table internalMacLookup {
        key = { std_meta.egress_spec: exact; }
        actions = {
            rewriteMacs;
            drop;
        }
        size = 256;
        default_action = drop;
    }

    action forward_to_port(bit<9> port) {
        std_meta.egress_spec = port;
    }

    table arpRoute {
        key = { hdr.arp.tpa: lpm; }
        actions = {
            forward_to_port;
            drop;
        }
        size = 16;
        default_action = drop;
    }

    table dhcpRoute {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = {
            forward_to_port;
            drop;
        }
        size = 16;
        default_action = drop;
    }

    apply {
        bool do_forward = false;
        bool l3_hit = false;

        // --- 1. Processamento de Protocolos de Controlo (ARP/DHCP) ---
        if (hdr.arp.isValid()) {
            // (Mantém a tua lógica de ARP igual)
            if (std_meta.ingress_port == LAN_PORT || std_meta.ingress_port == LAN_PORT2) {
                forward_to_port(ARP_PROXY_PORT);
            } else if (std_meta.ingress_port == ARP_PROXY_PORT) {
                arpRoute.apply();
            } else { drop(); }
        } else if (hdr.dhcp.isValid()) {
            // (Mantém a tua lógica de DHCP igual)
            if (hdr.dhcp.op == 1) {
                forward_to_port(DHCP_SERVER_PORT_CNF);
            } else if (hdr.dhcp.op == 2) {
                dhcpRoute.apply();
            } else { drop(); }
        } else if (!hdr.ipv4.isValid() || !hdr.transport.isValid()) {
            drop();
        } 
        
        // --- 2. Lógica de Slicing e Traffic Shaping (O teu Bumerangue Ativo) ---
        else {
            // Verifica se o destino existe na tabela L3
            if (ipv4Lpm.apply().hit) { l3_hit = true; }

            // Identifica o slice (necessário para saber qual medidor usar)
            slice_classifier.apply();

            // SÓ incrementamos o sliceCounter (Total) se o pacote for NOVO (não vier da porta 5)
            if (std_meta.ingress_port != TS_PORT) {
                sliceCounter.count((bit<32>)meta.slice_id);
            }

            // Executa o medidor para todos (Novos e Re-enviados)
            bit<32> meter_color = 0;
            if (meta.slice_id != 0) {
                sliceMeter.execute_meter((bit<32>)meta.slice_id, meter_color);
            }

            if (meter_color != 0) {
                forward_to_port(TS_PORT);
            } else {
                // VERDE: Pode passar! Incrementa o passedCounter (o que sai da rede)
                passedCounter.count((bit<32>)meta.slice_id);
                
                // Lógica de Firewall (Bloom Filter) e encaminhamento
                if (l3_hit) {
                    if (std_meta.ingress_port == LAN_PORT || std_meta.ingress_port == LAN_PORT2) {
                        computeHashes(hdr.ipv4.srcAddr, hdr.ipv4.dstAddr,
                                      hdr.transport.srcPort, hdr.transport.dstPort);
                        bloomFilter1.write(regPosOne, 1);
                        bloomFilter2.write(regPosTwo, 1);
                        do_forward = true;
                    } else if (std_meta.ingress_port == TS_PORT) {
                        // Se veio do TS e agora é verde, tratamos como se viesse da LAN original
                        // mas sem re-escrever o Bloom Filter (ou podes re-escrever para garantir)
                        do_forward = true;
                    } else {
                        // Tráfego de entrada (WAN -> LAN): verifica Firewall
                        computeHashes(hdr.ipv4.dstAddr, hdr.ipv4.srcAddr,
                                      hdr.transport.dstPort, hdr.transport.srcPort);
                        bloomFilter1.read(regValOne, regPosOne);
                        bloomFilter2.read(regValTwo, regPosTwo);
                        if (regValOne == 1 && regValTwo == 1) { do_forward = true; }
                        else { drop(); }
                    }
                }
            }
        } 

        if (do_forward) {
            internalMacLookup.apply();
            forwardedCounter.count(0);
        }
    }
}

// EGRESS ***********************************************************************

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t std_meta) {
    apply { 
        if (meta.slice_id == 3) {
            std_meta.priority = 1; // Gold
        } else if (meta.slice_id == 2) {
            std_meta.priority = 2; // Silver
        } else {
            std_meta.priority = 3; // Bronze / Outros
        }
    }
}

// CHECKSUM COMPUTATION *********************************************************

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version,
              hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

// DEPARSER *********************************************************************

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ether);
        packet.emit(hdr.arp);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.transport);
        packet.emit(hdr.udp_tail);
        packet.emit(hdr.dhcp);
    }
}

// SWITCH ***********************************************************************

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;