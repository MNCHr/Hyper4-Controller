#define VIBRANT_FLAG 0x020101010101

header_type vibrant_t {
  fields {
    flag : 48;
    hKeyIndex : 64; // choose 8
  }
}

header_type ethernet_t {
    fields {
        dstAddr : 48;
        srcAddr : 48;
        etherType : 16;
    }
}

header_type ipv4_t {
    fields {
        version : 4;
        ihl : 4;
        diffserv : 8;
        totalLen : 16;
        identification : 16;
        flags : 3;
        fragOffset : 13;
        ttl : 8;
        protocol : 8;
        hdrChecksum : 16;
        srcAddr : 32;
        dstAddr: 32;
    }
}

// This allows us to decrypt and switch/route using temp fields so
//  no need to re-encrypt before transmission, as we would have to
//  if we decrypted to parsed representation fields:
header_type meta_t {
  fields {
    eth_dstAddr : 48;
    eth_srcAddr : 48;
    ipv4_dstAddr : 32;
    ipv4_srcAddr : 32;
  }
}

header_type intrinsic_metadata_t {
  fields {
        ingress_global_timestamp : 48;
        lf_field_list : 8;
        mcast_grp : 16;
        egress_rid : 16;
        resubmit_flag : 8;
        recirculate_flag : 8;
  }
}

header vibrant_t vibrant;
header ethernet_t ethernet;
header ipv4_t ipv4;
metadata meta_t meta;
metadata intrinsic_metadata_t intrinsic_metadata;

parser start {
  extract(ethernet);
  return select(ethernet.etherType) {
    0x0800 : parse_ipv4;
    default: ingress;
  }
}

parser parse_ipv4 {
  extract(ipv4);
  return select(current(0, 48)) {
    VIBRANT_FLAG : parse_vibrant;
    default: ingress;
  }
}

parser parse_vibrant {
  extract(vibrant);
  return ingress;
}

action vibrant_present() { }
action vibrant_not_present() { }

table check_vibrant {
  reads {
    vibrant : valid;
  }
  actions {
    vibrant_present;
    vibrant_not_present;
  }
}

action a_decrypt(k1, k2, k3, k4) {
  bit_xor(meta.eth_dstAddr, ethernet.dstAddr, k1);
  bit_xor(meta.eth_srcAddr, ethernet.srcAddr, k2);
  bit_xor(meta.ipv4_dstAddr, ipv4.dstAddr, k3);
  bit_xor(meta.ipv4_srcAddr, ipv4.srcAddr, k4);
}

table decrypt {
  reads {
    vibrant.hKeyIndex : ternary;
  }
  actions {
    a_decrypt;
  }
}

action local(port) {
  modify_field(standard_metadata.egress_spec, port);
}

action not_local(port) {
  modify_field(standard_metadata.egress_spec, port);
}

action broadcast(mcast) {
  modify_field(intrinsic_metadata.mcast_grp, mcast);
}

action _drop() {
  drop();
}

table dmac {
  reads {
    meta.eth_dstAddr : exact;
  }
  actions {
    local;
    not_local;
    broadcast;
    _drop;
  }
}

action a_strip_vibrant() {
  modify_field(ethernet.dstAddr, meta.eth_dstAddr);
  modify_field(ethernet.srcAddr, meta.eth_srcAddr);
  modify_field(ipv4.dstAddr, meta.ipv4_dstAddr);
  modify_field(ipv4.srcAddr, meta.ipv4_srcAddr);
  remove_header(vibrant);
}

table strip_vibrant {
  actions {
    a_strip_vibrant;
  }
}

table dmac2 {
  reads {
    ethernet.dstAddr : exact;
  }
  actions {
    local;
    not_local;
    broadcast;
    _drop;
  }
}

action a_add_vibrant() {
  add_header(vibrant);
  modify_field(vibrant.flag, VIBRANT_FLAG);
  modify_field_rng_uniform(vibrant.hKeyIndex, 0, 0xFFFFFFFFFFFFFFFF);
}

action _no_op() { }

table add_vibrant {
  reads {
    ipv4 : valid;
  }
  actions {
    a_add_vibrant;
    _no_op;
  }
}

action a_encrypt(k1, k2, k3, k4) {
  bit_xor(ethernet.dstAddr, ethernet.dstAddr, k1);
  bit_xor(ethernet.srcAddr, ethernet.srcAddr, k2);
  bit_xor(ipv4.dstAddr, ipv4.dstAddr, k3);
  bit_xor(ipv4.srcAddr, ipv4.srcAddr, k4);
}

action a_mod_epoch_and_encrypt(new_epoch, k1, k2, k3, k4) {
  modify_field(vibrant.hKeyIndex, new_epoch);
  bit_xor(ethernet.dstAddr, ethernet.dstAddr, k1);
  bit_xor(ethernet.srcAddr, ethernet.srcAddr, k2);
  bit_xor(ipv4.dstAddr, ipv4.dstAddr, k3);
  bit_xor(ipv4.srcAddr, ipv4.srcAddr, k4);
}

table encrypt {
  reads {
    vibrant.hKeyIndex : ternary;
  }
  actions {
    a_encrypt;
    a_mod_epoch_and_encrypt;
  }
}

control ingress {
  apply(check_vibrant) {
    vibrant_present {
      apply(decrypt);
      apply(dmac) {
        local {
          apply(strip_vibrant);
        }
      }
    }
    vibrant_not_present {
      apply(dmac2) {
        not_local {
          apply(add_vibrant) {
            a_add_vibrant {
              apply(encrypt);
            }
          }
        }
      }
    }
  }
}
/*
table filter_egress {
  actions {
    _drop;
  }
}

control egress {
  if(standard_metadata.egress_port == standard_metadata.ingress_port) {
    apply(filter_egress);
  }
}
*/
